# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test EntitlementExchange and EntitlementImporter."""

__metaclass__ = type

import unittest
import logging
from cStringIO import StringIO

from zope.testing.loghandler import Handler

from canonical.testing import LaunchpadZopelessLayer
from canonical.launchpad import scripts
from canonical.launchpad.scripts.entitlement import (
    EntitlementExchange, EntitlementImporter,
    InvalidFormat, UnsupportedVersion)


class EntitlementExchangeTestCase(unittest.TestCase):
    """Test EntitlementExchange methods."""
    layer = LaunchpadZopelessLayer

    def test_preprocessData(self):
        """The preprocessor verifies the header and removes comments."""
        # Wrong header
        data = ("# bad format data\n"
                "more data")
        in_file = StringIO(data)
        self.assertRaises(
            InvalidFormat, EntitlementExchange._preprocessData, in_file)

        # Invalid version
        data = ("# Entitlement exchange format version 0\n"
                "more data")
        in_file = StringIO(data)
        self.assertRaises(
            UnsupportedVersion, EntitlementExchange._preprocessData, in_file)

        # Only one line should remain after processing
        data = ("# Entitlement exchange format version 1\n"
                "# comment line\n"
                "    # another comment\n"
                "'name', 'date' #valid line")
        in_file = StringIO(data)
        processed = EntitlementExchange._preprocessData(in_file)
        self.assertEqual(len(processed.split('\n')), 1)

class EntitlementImporterTestCase(unittest.TestCase):
    """Test EntitlementImport methods."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Setup the test environment and retrieve useful instances."""
        self.log = logging.getLogger("test_entitlement")
        self.log.setLevel(logging.INFO)
        self.handler = Handler(self)
        self.handler.add(self.log.name)

    def tearDown(self):
        """Teardown the test environment."""
        self.layer.txn.commit()
        self.handler.close()

    def _getImporterAndReader(self, data):
        in_file = StringIO(data)
        importer = EntitlementImporter(self.log)
        return importer, EntitlementExchange.readerFactory(in_file)

    def _testCreate(self, data):
        importer, reader = self._getImporterAndReader(data)
        return importer.createEntitlements(reader)

    def _testUpdate(self, data):
        importer, reader = self._getImporterAndReader(data)
        return importer.updateEntitlements(reader)

    def test_manipulateEntitlement(self):
        """Test creating and updating entitlements."""

    def test_wrongVersion(self):
        """Wrong version."""
        data = r"""# Entitlement exchange format version 0"""
        in_file = StringIO(data)
        importer = EntitlementImporter(self.log)
        self.assertRaises(UnsupportedVersion,
                          EntitlementExchange.readerFactory,
                          in_file)

    def test_successfulInsert(self):
        """Successfully insert an entitlement."""
        data = ("# Entitlement exchange format version 1\n"
                ",A-100, lifeless, 10, 100,  0, 2007-06-14, , , "
                "keybuk, keybuk, 20,")
        results = self._testCreate(data)
        self.assertEqual(len(results), 1)

    def test_insertUsingNonExistentPerson(self):
        """Attempt to insert using a non-existent person."""
        data = ("# Entitlement exchange format version 1\n"
                ",A-100, persona_non_grata, 10, 100,  0, 2007-06-14, , , "
                "keybuk, keybuk, 20,")
        results = self._testCreate(data)
        self.handler.assertLogsMessage(
            "[E0] Person 'persona_non_grata' "
            "is not found.", level=logging.ERROR)

    def test_omitQuota(self):
        """Omit the quota and get an error."""
        data = ("# Entitlement exchange format version 1\n"
                ",A-100, lifeless, 10, ,  0, 2007-06-14, , , "
                "keybuk, keybuk, 20,")
        results = self._testCreate(data)
        self.handler.assertLogsMessage(
            "[E0] A required key is missing: quota.",
            level=logging.ERROR)

    def test_omitPerson(self):
        """Omit the person and get an error."""
        data = ("# Entitlement exchange format version 1\n"
                ",A-100, , 10, 100,  0, 2007-06-14, , , "
                "keybuk, keybuk, 20,")
        results = self._testCreate(data)
        self.handler.assertLogsMessage(
            "[E0] A required key is missing: person_name.",
            level=logging.ERROR)

    def test_omitExtId(self):
        """Omit the ext_id and get an error."""
        data = ("# Entitlement exchange format version 1\n"
                ",, lifeless, 10, 100,  0, 2007-06-14, , , "
                "keybuk, keybuk, 20,")
        results = self._testCreate(data)
        self.handler.assertLogsMessage(
            "[E0] A required key is missing: ext_id.",
            level=logging.ERROR)

    def test_omitEntitlementType(self):
        """Omit the entitlement_type and get an error."""
        data = ("# Entitlement exchange format version 1\n"
                ",A-100, lifeless, , 100,  0, 2007-06-14, , , "
                "keybuk, keybuk, 20,")
        results = self._testCreate(data)
        self.handler.assertLogsMessage(
            "[E0] A required key is missing: entitlement_type.",
            level=logging.ERROR)

    def test_omitState(self):
        """Omit the state and get an error."""
        data = ("# Entitlement exchange format version 1\n"
                ",A-100, lifeless, 10, 100,  0, 2007-06-14, , , "
                "keybuk, keybuk, ,")
        results = self._testCreate(data)
        self.handler.assertLogsMessage(
            "[E0] A required key is missing: state.",
            level=logging.ERROR)

    def test_updateWithInvalidId(self):
        """Update using an invalid entitlement id."""
        data = ("# Entitlement exchange format version 1\n"
                "9999,A-100,kiko, ,1500, , , , , , , , ")
        results = self._testUpdate(data)
        self.handler.assertLogsMessage(
            "[E0] Invalid entitlement id: 9999",
            level=logging.ERROR)

    def test_updateChangingPerson(self):
        """Changing the person, which isn't allowed."""
        data = ("# Entitlement exchange format version 1\n"
                ",A-100, lifeless, 10, 100,  0, 2007-06-14, , , "
                "keybuk, keybuk, 20,")
        results = self._testCreate(data)
        self.assertEqual(len(results), 1)
        valid_id = results[0].get('id')
        data = ("# Entitlement exchange format version 1\n"
                " %s, A-100, kiko, , 1500, , , , , , , , " %
                valid_id)
        results = self._testUpdate(data)
        self.handler.assertLogsMessage(
            "[E0] You may not change the person for the entitlement.",
            level=logging.INFO)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
