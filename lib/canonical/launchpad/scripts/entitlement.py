# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Operate on entitlements."""

__metaclass__ = type
__all__ = [
    'EntitlementExchange',
    'EntitlementWriter',
    'NoSuchEntitlement',
    ]

from zope.component import getUtility

import cStringIO
import csv
import re

from canonical.database.sqlbase import flush_database_updates
from canonical.lp import initZopeless
from canonical.lp.dbschema import EntitlementState, EntitlementType
from canonical.launchpad.interfaces import IEntitlementSet, IPersonSet
from canonical.launchpad.utilities.unicode_csv import (
    UnicodeDictReader, UnicodeDictWriter
    )

COMMENT = '#'
COMMA = ','


class NoSuchEntitlement(Exception):
    """Used if a non-existent entitlement is specified."""


class UnsupportedVersion(Exception):
    """Used if the version is not supported."""


class InvalidFormat(Exception):
    """Used if the file format is not as expected."""


class EntitlementExchange:
    """Define the exchange format for entitlement data.

    Writers of entitlement data should use the 'writerFactory' method to
    obtain a writer object.  Readers should use the 'readerFactory'.  They
    return a UnicodeDictWriter and UnicodeDictReader respectively.

    Any changes to the list of fieldnames or their order will require an
    increment in the version value.
    """

    file_header = "%s Entitlement exchange format version" % COMMENT
    version = 1
    version_re = re.compile(
        "^%s (\d+)" % file_header)

    fieldnames = [
        'id', 'ext_id', 'person_name', 'entitlement_type', 'quota',
        'amount_used', 'date_starts', 'date_expires', 'date_created',
        'registrant_name', 'approved_by_name', 'state', 'whiteboard',
        ]

    @staticmethod
    def _checkVersion(read_version):
        """Check the version number.  Raise an exception if not supported."""
        supported = EntitlementExchange.version
        reported = read_version

        if supported != reported:
            # if the versions do not match then
            # an error has occured.
            raise UnsupportedVersion(
                "Version %d of the file format is not supported." %
                reported)
        else:
            # The version is supported
            return

    @staticmethod
    def _preprocessData(in_file):
        version_line = in_file.readline()
        match = EntitlementExchange.version_re.search(version_line)
        if not match:
            raise InvalidFormat(
                "The first line does not have valid version information.")
        read_version = int(match.group(1))
        EntitlementExchange._checkVersion(read_version)
        lines= [line for line in in_file.readlines()
                if not line.lstrip().startswith(COMMENT)]
        return "".join(lines)

    @staticmethod
    def readerFactory(in_file):
        """Return a properly provisioned reader factory.

        Assumes data in the file is UTF-8 encoded.
        """

        filedata = EntitlementExchange._preprocessData(in_file)
        return UnicodeDictReader(cStringIO.StringIO(filedata),
                                 EntitlementExchange.fieldnames,
                                 skipinitialspace=True,
                                 quoting=csv.QUOTE_ALL)

    @staticmethod
    def writerFactory(filedescriptor):
        filedescriptor.write(
            "%s %d\n" % (EntitlementExchange.file_header,
                         EntitlementExchange.version))
        filedescriptor.write(
            "%s %s\n" % (COMMENT,
                        COMMA.join(EntitlementExchange.fieldnames)))
        writer = UnicodeDictWriter(filedescriptor,
                                   EntitlementExchange.fieldnames,
                                   skipinitialspace=True,
                                   quoting=csv.QUOTE_ALL)
        return writer


class EntitlementWriter:
    """Class for writing and updating entitlement data.

    Methods create_entitlements and update_entitlements are called with a list
    of dictionaries representing entitlement data.
    """
    def __init__(self, logger):
        self.logger = logger

    def _normalizeEntitlement(self, entitlement, person_required=True):
        """Normalize a dictionary representing an entitlement.

        Convert names of people and teams to database objects and
        convert string representations of numerics to the correct type.
        Remove any keys in the dictionary that do not correspond to attributes
        on an Entitlement.
        """
        person_name = entitlement.get('person_name')
        if person_name is None:
            person = None
        else:
            person = getUtility(IPersonSet).getByName(person_name)
        if person_required and person is None:
            self.logger.error(
                "[E%d] Person %s is not found." % (self.row_no,
                                                   person_name))
            return None

        entitlement['person'] = person
        del entitlement['person_name']

        registrant_name = entitlement.get('registrant_name')
        if registrant_name is None:
            registrant = None
        else:
            registrant = getUtility(IPersonSet).getByName(registrant_name)
        if registrant is not None:
            entitlement['registrant'] = registrant
        del entitlement['registrant_name']

        approved_by_name = entitlement.get('approved_by_name')
        if approved_by_name is None:
            approved_by = None
        else:
            approved_by = getUtility(IPersonSet).getByName(approved_by_name)
        if approved_by is not None:
            entitlement['approved_by'] = approved_by
        del entitlement['approved_by_name']

        # Remove the 'ext_id' since it is not part of the Launchpad data.
        del entitlement['ext_id']

        # Convert numeric data from string to int.
        for field in ['id', 'quota', 'entitlement_type', 'state', 'amount_used']:
            if entitlement[field]:
                entitlement[field] = int(entitlement[field])

        # Convert the entitlement_type and state to the corresponding
        # database objects.
        if entitlement['entitlement_type']:
            entitlement_type = entitlement['entitlement_type']
            entitlement['entitlement_type'] = (
                EntitlementType.items.mapping[entitlement_type])

        if entitlement['state']:
            state = entitlement['state']
            entitlement['state'] = (
                EntitlementState.items.mapping[state])

        # Remove the entries from the dictionary that only have placeholder
        # data.
        for key, value in entitlement.items():
            if not value:
                del entitlement[key]
        return entitlement

    def _checkRequired(self, entitlement, required):
        for key in required:
            val = entitlement.get(key)
            if not val:
                self.logger.error(
                    "[E%d] A required key is missing : %s." % (self.row_no,
                                                               key))
                return False
        return True

    def createEntitlements(self, entitlements):
        """Create a new entitlement for each in the list."""

        required = ['ext_id', 'person_name', 'quota', 'entitlement_type',
                    'state']
        entitlement_set = getUtility(IEntitlementSet)
        new_entitlements = []
        for self.row_no, entitlement in enumerate(entitlements):
            if self._checkRequired(entitlement, required) is False:
                continue
            ext_id = entitlement.get('ext_id')
            normalized_entitlement = self._normalizeEntitlement(entitlement)
            if normalized_entitlement is None:
                continue

            new_entitlement = entitlement_set.new(**normalized_entitlement)

            if new_entitlement:
                new_entitlements.append(dict(id=str(new_entitlement.id),
                                             ext_id=ext_id))
        return new_entitlements

    def updateEntitlements(self, entitlements):
        """Update an existing entitlement.

        The entitlement must already exist.  A list of dictionaries with the
        ids of the entitlments that were modified is returned.
        """

        modified = []
        for self.row_no, upd_entitlement in enumerate(entitlements):
            required = ['id']
            if self._checkRequired(upd_entitlement, required) is False:
                continue
            # The ext_id must be cached before the data is normalized.
            ext_id = upd_entitlement.get('ext_id')
            norm_entitlement = self._normalizeEntitlement(
                upd_entitlement, person_required=False)
            if norm_entitlement is None:
                continue
            lpid = norm_entitlement.get('id')
            entitlement_set = getUtility(IEntitlementSet)

            existing = entitlement_set.get(lpid)
            succeeded = True
            for (key, val) in norm_entitlement.items():
                if key == 'id':
                    pass
                elif key == 'person':
                    self.logger.info(
                        "[E%d] You may not change the person for the "
                        "entitlement." % (self.row_no))
                elif key == 'entitlement_type':
                    existing.entitlement_type = val
                elif key == 'quota':
                    existing.quota = val
                    print "changing quota to %d" % existing.quota
                elif key == 'amount_used':
                    existing.amount_used = val
                elif key == 'date_starts':
                    existing.data_starts = val
                elif key == 'date_expires':
                    existing.date_expires = val
                elif key == 'date_created':
                    existing.date_created = val
                elif key == 'registrant':
                    existing.registrant = val
                elif key == 'approved_by':
                    existing.approved_by = val
                elif key == 'state':
                    existing.state = val
                elif key == 'whiteboard':
                    # Append the whiteboard value rather than replacing it.
                    existing.whiteboard = "%s\n%s" % (existing.whiteboard,
                                                      val)
                else:
                    self.logger.error(
                        "[E%d] Unrecognized key: %s." % (self.row_no, key))
                    succeeded = False
                    break
            if succeeded:
                modified.append(dict(id=str(lpid)))
        return modified
