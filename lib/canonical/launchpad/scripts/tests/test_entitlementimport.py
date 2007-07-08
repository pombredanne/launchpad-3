import unittest
from cStringIO import StringIO

from canonical.testing import LaunchpadZopelessLayer

from canonical.launchpad.scripts.entitlement import (
    EntitlementExchange, EntitlementImporter,
    InvalidFormat, UnsupportedVersion)
from canonical.lp.dbschema import (
    EntitlementState, EntitlementType)

class MockLogger:
    """Local log facility """
    def __init__(self):
        self.logs = []

    def read(self):
        """Return printable log contents and reset current log."""
        content = "\n".join(self.logs)
        self.logs = []
        return content

    def debug(self, txt):
        self.logs.append("DEBUG: %s" % txt)

    def info(self, txt):
        self.logs.append("INFO: %s" % txt)

    def error(self, txt):
        self.logs.append("ERROR: %s" % txt)

class EntitlementExchangeTestCase(unittest.TestCase):
    """Test EntitlementExchange methods."""
    layer = LaunchpadZopelessLayer

    def test_checkVersion(self):
        """ Test the version tester works for all cases."""
        version = EntitlementExchange.version
        check = EntitlementExchange._checkVersion(version)
        self.assertTrue(check)
        self.assertRaises(
            UnsupportedVersion, EntitlementExchange._checkVersion, version-1)
        self.assertRaises(
            UnsupportedVersion, EntitlementExchange._checkVersion, version+1)

    def test_preprocessData(self):
        """The preprocessor verifies the header and removes comments."""
        data = ("# bad format data\n"
                "more data")
        in_file = StringIO(data)
        self.assertRaises(
            InvalidFormat, EntitlementExchange._preprocessData, in_file)

        # Only one line should remain after processing
        data = ("# Entitlement exchange format version 1\n"
                "# comment line\n"
                "    # another comment\n"
                "'name', 'date' #valid line")
        in_file = StringIO(data)
        processed = EntitlementExchange._preprocessData(in_file)
        self.assertEqual(len(processed.split('\n')), 1)

class EntitlementImporterTestCase(unittest.TestCase):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Setup the test environment and retrieve useful instances."""
        self.log = MockLogger()

    def test_updateEntitlement(self):
        # Wrong version.
        data = r"""# Entitlement exchange format version 0"""
        in_file = StringIO(data)
        importer = EntitlementImporter(self.log)
        self.assertRaises(UnsupportedVersion,
                          EntitlementExchange.readerFactory,
                          in_file)

        # Successfully insert an entitlement.
        data = ("""# Entitlement exchange format version 1\n"""
                """,A-100, lifeless, 10, 100,  0, 2007-06-14, , , """
                """keybuk, keybuk, 20,""")
        in_file = StringIO(data)
        importer = EntitlementImporter(self.log)
        reader = EntitlementExchange.readerFactory(in_file)
        results = importer.createEntitlements(reader)
        self.assertEqual(len(results), 1)
        valid_id = results[0].get('id')

        # Attempt to insert using a non-existent person.
        data = ("""# Entitlement exchange format version 1\n"""
                """,A-100, persona_non_grata, 10, 100,  0, 2007-06-14, , , """
                """keybuk, keybuk, 20,""")
        in_file = StringIO(data)
        importer = EntitlementImporter(self.log)
        reader = EntitlementExchange.readerFactory(in_file)
        results = importer.createEntitlements(reader)
        self.assertEqual(self.log.read(),
                         "ERROR: [E0] Person 'persona_non_grata' "
                         "is not found.")

        # Omit the quota and get an error.
        data = ("""# Entitlement exchange format version 1\n"""
                """,A-100, lifeless, 10, ,  0, 2007-06-14, , , """
                """keybuk, keybuk, 20,""")
        in_file = StringIO(data)
        importer = EntitlementImporter(self.log)
        reader = EntitlementExchange.readerFactory(in_file)
        results = importer.createEntitlements(reader)
        self.assertEqual(self.log.read(),
                         "ERROR: [E0] A required key is missing: quota.")

        # Omit the person and get an error.
        data = ("""# Entitlement exchange format version 1\n"""
                """,A-100, , 10, 100,  0, 2007-06-14, , , """
                """keybuk, keybuk, 20,""")
        in_file = StringIO(data)
        importer = EntitlementImporter(self.log)
        reader = EntitlementExchange.readerFactory(in_file)
        results = importer.createEntitlements(reader)
        self.assertEqual(self.log.read(),
                         "ERROR: [E0] A required key is missing: "
                         "person_name.")

        # Omit the ext_id and get an error.
        data = ("""# Entitlement exchange format version 1\n"""
                """,, lifeless, 10, 100,  0, 2007-06-14, , , """
                """keybuk, keybuk, 20,""")
        in_file = StringIO(data)
        importer = EntitlementImporter(self.log)
        reader = EntitlementExchange.readerFactory(in_file)
        results = importer.createEntitlements(reader)
        self.assertEqual(self.log.read(),
                         "ERROR: [E0] A required key is missing: ext_id.")

        # Omit the entitlement_type and get an error.
        data = ("""# Entitlement exchange format version 1\n"""
                """,A-100, lifeless, , 100,  0, 2007-06-14, , , """
                """keybuk, keybuk, 20,""")
        in_file = StringIO(data)
        importer = EntitlementImporter(self.log)
        reader = EntitlementExchange.readerFactory(in_file)
        results = importer.createEntitlements(reader)
        self.assertEqual(self.log.read(),
                         "ERROR: [E0] A required key is missing: "
                         "entitlement_type.")

        # Omit the state and get an error.
        data = ("""# Entitlement exchange format version 1\n"""
                """,A-100, lifeless, 10, 100,  0, 2007-06-14, , , """
                """keybuk, keybuk, ,""")
        in_file = StringIO(data)
        importer = EntitlementImporter(self.log)
        reader = EntitlementExchange.readerFactory(in_file)
        results = importer.createEntitlements(reader)
        self.assertEqual(self.log.read(),
                         "ERROR: [E0] A required key is missing: "
                         "state.")

        # Update using an invalid entitlement id.
        data = ("""# Entitlement exchange format version 1\n"""
                """ "9999","A-100","kiko","","1500","","","","","","","",""""")
        in_file = StringIO(data)
        importer = EntitlementImporter(self.log)
        reader = EntitlementExchange.readerFactory(in_file)
        importer.updateEntitlements(reader)
        self.assertEqual(self.log.read(),
                         "ERROR: [E0] Invalid entitlement id: 9999")

        # Changing the person, which isn't allowed.
        data = ("""# Entitlement exchange format version 1\n"""
                """ "%s","A-100","kiko","","1500","","","","","","","",""""" %
                valid_id)

        in_file = StringIO(data)
        importer = EntitlementImporter(self.log)
        reader = EntitlementExchange.readerFactory(in_file)
        importer.updateEntitlements(reader)
        self.assertEqual(self.log.read(),
                         "INFO: [E0] You may not change the person "
                         "for the entitlement.")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
