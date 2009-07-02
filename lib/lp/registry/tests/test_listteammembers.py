import unittest

from canonical.testing import LaunchpadZopelessLayer

from lp.registry.scripts import listteammembers

ubuntuteam_default = [
    u'cprov, celso.providelo@canonical.com',
    u'edgar, edgar@monteparadiso.hr',
    u'jdub, jeff.waugh@ubuntulinux.com',
    u'kamion, colin.watson@ubuntulinux.com',
    u'kinnison, daniel.silverstone@canonical.com',
    u'limi, limi@plone.org', 
    u'name16, foo.bar@canonical.com',
    u'sabdfl, mark@hbd.com',
    u'stevea, steve.alexander@ubuntulinux.com',
    u'warty-gnome, --none--',
    ]

ubuntuteam_email = [
    u'admin@canonical.com',
    u'celso.providelo@canonical.com',
    u'colin.watson@ubuntulinux.com',
    u'cprov@ubuntu.com',
    u'daniel.silverstone@canonical.com',
    u'edgar@monteparadiso.hr',
    u'foo.bar@canonical.com',
    u'jeff.waugh@ubuntulinux.com',
    u'limi@plone.org', 
    u'mark@hbd.com',
    u'steve.alexander@ubuntulinux.com',
    ]

ubuntuteam_full = [
    u'ubuntu-team|10|limi|limi@plone.org|Alexander Limi|no',
    u'ubuntu-team|11|stevea|steve.alexander@ubuntulinux.com|Steve Alexander|no',
    u'ubuntu-team|16|name16|foo.bar@canonical.com|Foo Bar|yes',
    u'ubuntu-team|19|warty-gnome|--none--|Warty Gnome Team|no',
    u'ubuntu-team|1|sabdfl|mark@hbd.com|Mark Shuttleworth|no',
    u'ubuntu-team|26|kinnison|daniel.silverstone@canonical.com|Daniel Silverstone|no',
    u'ubuntu-team|28|cprov|celso.providelo@canonical.com|Celso Providelo|no',
    u'ubuntu-team|33|edgar|edgar@monteparadiso.hr|Edgar Bursic|no',
    u'ubuntu-team|4|kamion|colin.watson@ubuntulinux.com|Colin Watson|no',
    u'ubuntu-team|6|jdub|jeff.waugh@ubuntulinux.com|Jeff Waugh|no',
    ]

ubuntuteam_sshkeys = [
    u'sabdfl: ssh-dss AAAAB3NzaC1kc3MAAABBAL5VoWG5sy3CnLYeOw47L8m9A15hA/PzdX2u0B7c2Z1ktFPcEaEuKbLqKVSkXpYm7YwKj9y88A9Qm61CdvI0c50AAAAVAKGY0YON9dEFH3DzeVYHVEBGFGfVAAAAQCoe0RhBcefm4YiyQVwMAxwTlgySTk7FSk6GZ95EZ5Q8/OTdViTaalvGXaRIsBdaQamHEBB+Vek/VpnF1UGGm8YAAABAaCXDl0r1k93JhnMdF0ap4UJQ2/NnqCyoE8Xd5KdUWWwqwGdMzqB1NOeKN6ladIAXRggLc2E00UsnUXh3GE3Rgw== Private key in lib/lp/codehosting/tests/id_dsa',
    ]


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

    def test_listteammembers_sshkeys(self):
        """Test the ssh keys option."""
        self.assertEqual(
            listteammembers.process_team('ubuntu-team', 'sshkeys'), ubuntuteam_sshkeys)

    def test_listteammembers_unknown_team(self):
        """Test unknown team."""
        self.assertRaises(
            listteammembers.NoSuchTeamError, listteammembers.process_team, 'nosuchteam-matey')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
