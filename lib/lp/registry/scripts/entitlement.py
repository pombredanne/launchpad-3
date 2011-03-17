# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Import entitlements from Salesforce.

Provide a class that allows the writing and reading of entitlement exchange
files and a class to create and update entitlements in Launchpad.
"""

__metaclass__ = type
__all__ = [
    'EntitlementExchange',
    'EntitlementImporter',
    'InvalidFormat',
    'NoSuchEntitlement',
    'UnsupportedVersion',
    ]

import cStringIO
import csv
import datetime
import re
import time

import pytz
from zope.component import getUtility

from canonical.launchpad.utilities.unicode_csv import (
    UnicodeDictReader,
    UnicodeDictWriter,
    )
from lp.app.errors import NotFoundError
from lp.registry.interfaces.entitlement import (
    EntitlementState,
    EntitlementType,
    IEntitlementSet,
    )
from lp.registry.interfaces.person import IPersonSet


COMMENT = '#'
COMMA = ','


class NoSuchEntitlement(Exception):
    """Used if a non-existent entitlement is specified."""


class UnsupportedVersion(Exception):
    """Used if the version is not supported."""


class InvalidFormat(Exception):
    """Used if the file format is not as expected."""


class RequiredValueMissing(Exception):
    """Used if a required value was not provided."""


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
    def _preprocessData(in_file):
        """Verify the version and remove comments."""
        version_line = in_file.readline()
        match = EntitlementExchange.version_re.search(version_line)
        if not match:
            raise InvalidFormat(
                "The first line does not have valid version information.")
        read_version = int(match.group(1))
        if EntitlementExchange.version != read_version:
            raise UnsupportedVersion(
                "Version %d of the file format is not supported." %
                read_version)
        lines= [line for line in in_file.readlines()
                if not line.lstrip().startswith(COMMENT)]
        return "".join(lines)

    @staticmethod
    def readerFactory(in_file):
        """Return a properly provisioned reader.

        Assumes data in the file is UTF-8 encoded.
        """

        filedata = EntitlementExchange._preprocessData(in_file)
        return UnicodeDictReader(cStringIO.StringIO(filedata),
                                 EntitlementExchange.fieldnames,
                                 skipinitialspace=True,
                                 quoting=csv.QUOTE_ALL)

    @staticmethod
    def writerFactory(filedescriptor):
        """Return a properly provisioned writer.

        Data in the file will be UTF-8 encoded.
        """

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


class EntitlementImporter:
    """Class for writing and updating entitlement data.

    Methods create_entitlements and update_entitlements are called with a list
    of dictionaries representing entitlement data.
    """
    def __init__(self, logger):
        self.logger = logger

    def _replacePersonName(self, entitlement, old_key, new_key,
                           row_no, required=False):
        """Replace a person's name with a Person object in the entitlement.

        Raise RequiredValueMissing if the old_key is not found in the
        entitlement dictionary and required is True.
        Raise NotFoundError if no matching person can be found.
        """
        person_name = entitlement.get(old_key, '')
        del entitlement[old_key]
        if person_name == '':
            if required:
                raise RequiredValueMissing(
                    "'person_name' not supplied in row %d." % row_no)
            else:
                return entitlement
        person = getUtility(IPersonSet).getByName(person_name)
        if person is None:
            self.logger.error(
                "[E%d] Person '%s' is not found." % (
                row_no, person_name))
            raise NotFoundError(
                "Person '%s' not supplied in row %d." % (
                person_name, row_no))
        entitlement[new_key] = person
        return entitlement

    def _normalizeEntitlement(
        self, entitlement, row_no, person_required=True):
        """Normalize a dictionary representing an entitlement.

        Convert names of people and teams to database objects and
        convert string representations of numerics to the correct type.
        Remove any keys in the dictionary that do not correspond to attributes
        on an Entitlement.
        """
        entitlement = self._replacePersonName(
            entitlement, 'person_name', 'person', row_no, person_required)
        entitlement = self._replacePersonName(
            entitlement, 'registrant_name', 'registrant', row_no)
        entitlement = self._replacePersonName(
            entitlement, 'approved_by_name', 'approved_by', row_no)

        # Remove the 'ext_id' since it is not part of the Launchpad data.
        del entitlement['ext_id']

        # Convert numeric data from string to int.
        for field in ['id', 'quota', 'entitlement_type', 'state', 'amount_used']:
            if entitlement[field]:
                entitlement[field] = int(entitlement[field])

        # Convert strings to dates.
        for field in ['date_starts', 'date_expires', 'date_created']:
            if entitlement[field]:
                date_string = entitlement[field]
                if len(date_string) == len('YYYY-mm-dd'):
                    year, month, day, hour, minute, second = time.strptime(
                        date_string, '%Y-%m-%d')[:6]
                elif len(date_string) == len('YYYY-mm-dd HH:MM:SS'):
                    year, month, day, hour, minute, second = time.strptime(
                        date_string, '%Y-%m-%d %H:%M:%S')[:6]
                else:
                    raise AssertionError(
                        'Unknown date format: %s' % date_string)
                entitlement[field] = datetime.datetime(
                    year, month, day, hour, minute, second,
                    tzinfo=pytz.timezone('UTC'))

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
            if value == '':
                del entitlement[key]
        return entitlement

    def _checkRequired(self, entitlement, required, row_no):
        """Check to see that all required keys are in the entitlement."""
        for key in required:
            val = entitlement.get(key, '')
            # Test for None or ''.  No boolean variable are expected.
            if val == '':
                self.logger.error(
                    "[E%d] A required key is missing: %s." % (row_no, key))
                return False
        return True

    def createEntitlements(self, entitlements):
        """Create a new entitlement for each in the list.

        Return a list of sparsely populated dictionaries suitable for writing
        as a return CSV file.
        """

        required = ['ext_id', 'person_name', 'quota', 'entitlement_type',
                    'state']
        entitlement_set = getUtility(IEntitlementSet)
        new_entitlements = []
        for row_no, entitlement in enumerate(entitlements):
            if self._checkRequired(entitlement, required, row_no) is False:
                continue
            ext_id = entitlement.get('ext_id')
            try:
                normalized_entitlement = self._normalizeEntitlement(
                    entitlement, row_no)
            except NotFoundError:
                continue
            except RequiredValueMissing:
                continue

            new_entitlement = entitlement_set.new(**normalized_entitlement)

            if new_entitlement is not None:
                # Add a dictionary with id and ext_id to the list of
                # new entitlements.
                new_entitlements.append(dict(id=str(new_entitlement.id),
                                             ext_id=ext_id))
        return new_entitlements

    def updateEntitlements(self, entitlements):
        """Update an existing entitlement.

        The entitlement must already exist.  A list of dictionaries with the
        ids of the entitlments that were modified is returned.
        """

        modified = []
        required = ['id']
        for row_no, upd_entitlement in enumerate(entitlements):
            if not self._checkRequired(upd_entitlement, required, row_no):
                continue
            # The ext_id must be cached before the data is normalized.
            ext_id = upd_entitlement.get('ext_id')

            try:
                norm_entitlement = self._normalizeEntitlement(
                    upd_entitlement, row_no, person_required=False)
            except NotFoundError:
                continue
            except RequiredValueMissing:
                continue

            lp_id = norm_entitlement.get('id')
            entitlement_set = getUtility(IEntitlementSet)

            existing = entitlement_set.get(lp_id)
            if existing is None:
                self.logger.error(
                    "[E%d] Invalid entitlement id: %d" % (row_no,
                                                          lp_id))
                continue

            succeeded = True
            for (key, val) in norm_entitlement.items():
                if key == 'id':
                    pass
                elif key == 'person':
                    self.logger.info(
                        "[E%d] You may not change the person for the "
                        "entitlement." % (row_no))
                    succeeded = False
                    break
                elif key == 'whiteboard':
                    # Append the whiteboard value rather than replacing it.
                    existing.whiteboard = "%s\n%s" % (existing.whiteboard,
                                                      val)
                elif key in ['entitlement_type', 'quota', 'amount_used',
                             'date_starts', 'date_expires', 'date_created',
                             'registrant', 'approved_by', 'state']:
                    setattr(existing, key, val)
                else:
                    self.logger.error(
                        "[E%d] Unrecognized key: %s." % (row_no, key))
                    succeeded = False
                    break
            if succeeded:
                modified.append(dict(id=str(lp_id)))
        return modified
