import unittest

from canonical.testing import LaunchpadZopelessLayer

from canonical.launchpad.scripts import listteammembers

ubuntuteam_default = ['cprov, celso.providelo@canonical.com'
            , 'jdub, jeff.waugh@ubuntulinux.com'
            , 'kamion, colin.watson@ubuntulinux.com'
            , 'kinnison, daniel.silverstone@canonical.com'
            , 'limi, --none--'
            , 'name16, foo.bar@canonical.com'
            , 'sabdfl, mark@hbd.com'
            , 'stevea, --none--']

ubuntuteam_email = ['celso.providelo@canonical.com'
            , 'colin.watson@ubuntulinux.com'
            , 'cprov@ubuntu.com'
            , 'daniel.silverstone@canonical.com'
            , 'foo.bar@canonical.com'
            , 'jeff.waugh@ubuntulinux.com'
            , 'mark@hbd.com']

ubuntuteam_full = ['ubuntu-team|10|limi|--none--|Alexander Limi|no'
            , 'ubuntu-team|11|stevea|--none--|Steve Alexander|no'
            , 'ubuntu-team|16|name16|foo.bar@canonical.com|Foo Bar|yes'
            , 'ubuntu-team|1|sabdfl|mark@hbd.com|Mark Shuttleworth|no'
            , 'ubuntu-team|26|kinnison|daniel.silverstone@canonical.com|Daniel Silverstone|no'
            , 'ubuntu-team|28|cprov|celso.providelo@canonical.com|Celso Providelo|no'
            , 'ubuntu-team|4|kamion|colin.watson@ubuntulinux.com|Colin Watson|no'
            , 'ubuntu-team|6|jdub|jeff.waugh@ubuntulinux.com|Jeff Waugh|no']

class ListTeamMembersTestCase(unittest.TestCase):
    """Test listing team members"""
    layer = LaunchpadZopelessLayer

    def test_default_list(self):
        """Test the default option"""
        self.assertEqual(listteammembers.process_team('ubuntu-team'), ubuntuteam_default)       
    
    def test_email_only(self):
        """Test the email only option"""
        self.assertEqual(listteammembers.process_team('ubuntu-team', 'email'), ubuntuteam_email)

    def test_full_details(self):
        """Test the full details option"""
        self.assertEqual(listteammembers.process_team('ubuntu-team', 'full'), ubuntuteam_full)

    def test_unknown_team(self):
        """Test unknown team"""
        self.assertRaises(listteammembers.NoSuchTeamError, listteammembers.process_team, 'nosuchteam-matey')
        # This should fail
        self.assertRaises(listteammembers.NoSuchTeamError, listteammembers.process_team, 'ubuntu-team')
        
def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
