import unittest
import getpass

from canonical.database.sqlbase import connect
from canonical.launchpad.scripts.scriptmonitor import check_script


class CheckScriptTestCase(unittest.TestCase):
    """Test script activity."""
    con = connect(getpass.getuser())

    def test_scriptfound(self):
        self.assertEqual(
            check_script(con, log, 'localhost', 'test-script',
                '2007-05-23 00:30:00', '2007-05-23 01:30:00'), None)

    def test_scriptnotfound_timing(self):
        self.assertRaises(
            check_script(con, log, 'localhost', 'test-script',
                '2007-05-23 01:30:00', '2007-05-23 02:30:00'))

    def test_scriptnotfound_hostname(self):
        self.assertRaises(
            check_script(con, log, 'notlocalhost', 'test-script',
                '2007-05-23 00:30:00', '2007-05-23 01:30:00'))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
