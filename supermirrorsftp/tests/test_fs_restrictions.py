
import os
import shutil

from twisted.trial import unittest
from twisted.vfs.ivfs import VFSError, PermissionError

from supermirrorsftp.sftponly import SFTPOnlyAvatar
from supermirrorsftp.bazaarfs import SFTPServerRoot

class AvatarTestBase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = self.mktemp()
        os.mkdir(self.tmpdir)
        # A basic user dict, a member of no teams (aside from the user
        # themself).
        self.aliceUserDict = {
            'id': 1, 
            'name': 'alice', 
            'teams': [{'id': 1, 'name': 'alice'}],
        }

        # An slightly more complex user dict for a user that is also a member of
        # a team.
        self.bobUserDict = {
            'id': 2, 
            'name': 'bob', 
            'teams': [{'id': 2, 'name': 'bob'},
                      {'id': 3, 'name': 'test-team'}],
        }

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

class TestTopLevelDir(AvatarTestBase):
    def testListDirNoTeams(self):
        # list only user dir + team dirs
        avatar = SFTPOnlyAvatar('alice', self.tmpdir, '/dev/null',
                                self.aliceUserDict)
        root = SFTPServerRoot(avatar)
        self.assertEqual(
            [name for name, child in root.children()], 
            ['.', '..', '~alice'])

    def testListDirTeams(self):
        # list only user dir + team dirs
        
        # Add a team to Alice's user dict
        avatar = SFTPOnlyAvatar('bob', self.tmpdir, '/dev/null',
                                self.bobUserDict)
        root = SFTPServerRoot(avatar)
        self.assertEqual(
            [name for name, child in root.children()], 
            ['.', '..', '~bob', '~test-team'])

    def testAllWriteOpsForbidden(self):
        avatar = SFTPOnlyAvatar('alice', self.tmpdir, '/dev/null',
                                self.aliceUserDict)
        root = SFTPServerRoot(avatar)
        self.assertRaises(PermissionError, root.createDirectory, 'xyz')
        self.assertRaises(PermissionError, root.createFile, 'xyz')
        self.assertRaises(PermissionError, root.child('~alice').remove)

    def testUserDirPlusJunk(self):
        avatar = SFTPOnlyAvatar('alice', self.tmpdir, '/dev/null',
                                self.aliceUserDict)
        root = avatar.filesystem.root
        userDir = root.child('~alice')
        userDir.createDirectory('+junk')
        self.assertEqual(
            [name for name, child in userDir.children()], 
            ['.', '..', '+junk'])

    def testTeamDirPlusJunk(self):
        avatar = SFTPOnlyAvatar('bob', self.tmpdir, '/dev/null',
                                self.bobUserDict)
        root = avatar.filesystem.root
        userDir = root.child('~test-team')
        self.assertRaises(PermissionError, userDir.createDirectory, '+junk')


class UserDirsTestCase(AvatarTestBase):
    def testCreateValidProduct(self): pass
    def testCreateInvalidProduct(self): pass

#class TeamDirsTestCase(AvatarTestBase):
#    """Same as UserDirsTestCase, except with a team dir."""
    
