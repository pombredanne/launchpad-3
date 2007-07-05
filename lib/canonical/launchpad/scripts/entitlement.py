# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Operate on entitlements."""

__metaclass__ = type
__all__ = [
    'create_entitlements',
    'delete_entitlements',
    'update_entitlements',
    'EntitlementExchange',
    'NoSuchEntitlement',    
    ]

from zope.component import getUtility
from zope.interface import Interface

import csv
import re

from canonical.database.sqlbase import flush_database_updates
from canonical.lp import initZopeless
from canonical.lp.dbschema import EntitlementState, EntitlementType
from canonical.launchpad.interfaces import IEntitlementSet, IPersonSet

COMMENT = '#'

class NoSuchEntitlement(Exception): 
    """Used if a non-existent entitlement is specified."""


class UnsupportedVersion(Exception): 
    """Used if the version is not supported."""


class InvalidFormat(Exception): 
    """Used if the file format is not as expected."""


class IEntitlementExchange(Interface):
    def _preprocessData(in_file):
        """Remove comments and verify the version."""
    def readerFactory(in_file, action):
        """Produce a reader for the in_file based on the action."""
    def writerFactory(in_file, action):
        """Produce a writer for the in_file based on the action."""
    
class EntitlementExchange:
    file_header = "# Entitlement exchange format version"
    version = (1,1)
    version_re = re.compile(
        "^%s (\d+)\.(\d+)" % file_header)

    fieldnames = [
        'id', 'ext_id', 'person_name', 'entitlement_type', 'quota', 
        'amount_used', 'date_starts', 'date_expires', 'date_created', 
        'registrant_name', 'approved_by_name', 'state', 'whiteboard',
        ]

    @staticmethod
    def _checkVersion(read_version):
        """Check the version number.  Raise an exception if not supported."""
        supported_major, supported_minor = EntitlementExchange.version
        reported_major, reported_minor = read_version

        if supported_major != reported_major:
            # if the major versions do not match then
            # an error has occured.
            raise UnsupportedVersion(
                "Major version %d of the file format is not supported." %
                reported_major)
        elif reported_minor > supported_minor:
            raise UnsupportedVersion(
                "Version %d.%d of the file format is not supported." %
                reported_major, reported_minor)
        else:
            # The version is supported
            return

    @staticmethod
    def encode_data(csv_data):
        for line in csv_data:
            yield line.encode('utf_8')

    @staticmethod
    def encode_dictionary(data):
        for key, value in data.items():
            data[key] = value.encode('utf_8')
        return data
    
    @staticmethod
    def _preprocessData(in_file):
        version_line = in_file.readline()
        match = EntitlementExchange.version_re.search(version_line)
        if not match:
            raise InvalidFormat(
                "The first line does not have valid version information.")
        read_version = tuple(int(version_part)
                             for version_part in match.groups())
        EntitlementExchange._checkVersion(read_version)
        return [line for line in in_file.readlines()
                if not line.lstrip().startswith(COMMENT)]
    
    @staticmethod
    def readerFactory(filedata):
        filedata = EntitlementExchange._preprocessData(filedata)
        return csv.DictReader(filedata,
                              EntitlementExchange.fieldnames,
                              #EntitlementExchange.encode_data(filedata),
                              skipinitialspace=True,
                              quoting=csv.QUOTE_ALL)
    
    @staticmethod
    def writerFactory(filedescriptor):
        filedescriptor.write(
            "%s %d.%d\n" % (EntitlementExchange.file_header,
                            EntitlementExchange.version[0],
                            EntitlementExchange.version[1]))
        writer = csv.DictWriter(filedescriptor,
                                EntitlementExchange.fieldnames,
                                skipinitialspace=True,
                                quoting=csv.QUOTE_ALL)
        return writer

def create_entitlements(entitlements):

    entitlement_set = getUtility(IEntitlementSet)
    new_entitlements = dict()
    for entitlement in entitlements:
        print entitlement
        person_name = entitlement.get('person_name')
        if person_name is None:
            person = None
        else:
            person = getUtility(IPersonSet).getByName(person_name)
        if person is None:
            continue

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

        ext_id = entitlement['ext_id']
        del entitlement['ext_id']

        # Convert numeric data from string to int
        for field in ['quota', 'entitlement_type', 'state', 'amount_used']:
            if entitlement[field]:
                entitlement[field] = int(entitlement[field])

        # Convert the entitlement_type and state to the corresponding
        # database objects
        if entitlement['entitlement_type']:
            entitlement_type = entitlement['entitlement_type']
            entitlement['entitlement_type'] = (
                EntitlementType.items.mapping[entitlement_type])

        if entitlement['state']:
            state = entitlement['state']
            entitlement['state'] = (
                EntitlementState.items.mapping[state])

        # remove the entries from the dictionary that only have placeholder
        # data
        for key, value in entitlement.items():
            if not value:
                del entitlement[key]
        print "keywords:\n", entitlement
        new_entitlement = entitlement_set.new(**entitlement)

        if new_entitlement:
            new_entitlements[new_entitlement.id] = ext_id
    return new_entitlements

def update_entitlements(entitlements):
    print "Update:"
    for entitlement in entitlements:
        print entitlement
    
