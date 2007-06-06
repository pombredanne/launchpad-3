import unittest

from canonical.testing import LaunchpadZopelessLayer

class ListTeamMembersTestCase(unittest.TestCase):
    """Test listing team members"""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Create two teams with two members that we can test"""

    def tearDown(self):
        """Get rid of the test teams"""

    def testDefaultList(self):
        """Test the default option"""
    
    def testEmailOnly(self):
        """Test the email only option"""

    def testFullDetails(self):
        """Test the full details option"""

    def testUnknownTeam(self):
        """Test unknown team"""
        
        

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
