import unittest

from canonical.testing import LaunchpadZopelessLayer

from canonical.launchpad.scripts import listteammembers

ubuntuteam_default = [
    u'cprov, celso.providelo@canonical.com',
    u'jdub, jeff.waugh@ubuntulinux.com',
    u'kamion, colin.watson@ubuntulinux.com',
    u'kinnison, daniel.silverstone@canonical.com',
    u'launchpad-beta-owner, beta-admin@launchpad.net',
    u'launchpad-beta-testers, --none--',
    u'limi, --none--',
    u'name16, foo.bar@canonical.com',
    u'sabdfl, mark@hbd.com',
    u'stevea, --none--']

ubuntuteam_email = [
    u'beta-admin@launchpad.net',
    u'celso.providelo@canonical.com',
    u'colin.watson@ubuntulinux.com',
    u'cprov@ubuntu.com',
    u'daniel.silverstone@canonical.com',
    u'foo.bar@canonical.com',
    u'jeff.waugh@ubuntulinux.com',
    u'mark@hbd.com']

ubuntuteam_full = [
    u'ubuntu-team|10|limi|--none--|Alexander Limi|no',
    u'ubuntu-team|11|stevea|--none--|Steve Alexander|no',
    u'ubuntu-team|16|name16|foo.bar@canonical.com|Foo Bar|yes',
    u'ubuntu-team|1|sabdfl|mark@hbd.com|Mark Shuttleworth|no',
    u'ubuntu-team|26|kinnison|daniel.silverstone@canonical.com|Daniel Silverstone|no',
    u'ubuntu-team|28|cprov|celso.providelo@canonical.com|Celso Providelo|no',
    u'ubuntu-team|4|kamion|colin.watson@ubuntulinux.com|Colin Watson|no',
    u'ubuntu-team|68|launchpad-beta-owner|beta-admin@launchpad.net|Launchpad Beta Testers Owner|no',
    u'ubuntu-team|69|launchpad-beta-testers|--none--|Launchpad Beta Testers|no',
    u'ubuntu-team|6|jdub|jeff.waugh@ubuntulinux.com|Jeff Waugh|no']


class ListTeamMembersTestCase(unittest.TestCase):
    """Test listing team members."""
    layer = LaunchpadZopelessLayer

    def test_listteammembers_default_list(self):
        """Test the default option."""
        self.assertEqual(
            listteammembers.process_team('ubuntu-team'), ubuntuteam_default)

    def test_listteammembers_email_only(self):
        """Test the email only option."""
        self.assertEqual(
            listteammembers.process_team('ubuntu-team', 'email'), ubuntuteam_email)

    def test_listteammembers_full_details(self):
        """Test the full details option."""
        self.assertEqual(
            listteammembers.process_team('ubuntu-team', 'full'), ubuntuteam_full)

    def test_listteammembers_unknown_team(self):
        """Test unknown team."""
        self.assertRaises(
            listteammembers.NoSuchTeamError, listteammembers.process_team, 'nosuchteam-matey')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
