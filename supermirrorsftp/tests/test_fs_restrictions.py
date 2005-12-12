
import os
import shutil

from twisted.trial import unittest
from twisted.internet import defer
from twisted.vfs.ivfs import VFSError, PermissionError

from supermirrorsftp.sftponly import SFTPOnlyAvatar
from supermirrorsftp.bazaarfs import SFTPServerRoot, SFTPServerBranch

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
        # XXX: all tests that use 'None' for the launchpad interface should
        # perhaps have a special mock object that asserts on any getattr, to
        # assert that the lp interface isn't used for certain ops?
        avatar = SFTPOnlyAvatar('alice', self.tmpdir, self.aliceUserDict, None)
        root = SFTPServerRoot(avatar)
        self.assertEqual(
            [name for name, child in root.children()], 
            ['.', '..', '~alice'])

    def testListDirTeams(self):
        # list only user dir + team dirs
        
        # Add a team to Alice's user dict
        avatar = SFTPOnlyAvatar('bob', self.tmpdir, self.bobUserDict, None)
        root = SFTPServerRoot(avatar)
        self.assertEqual(
            [name for name, child in root.children()], 
            ['.', '..', '~bob', '~test-team'])

    def testAllWriteOpsForbidden(self):
        avatar = SFTPOnlyAvatar('alice', self.tmpdir, self.aliceUserDict, None)
        root = SFTPServerRoot(avatar)
        self.assertRaises(PermissionError, root.createFile, 'xyz')
        self.assertRaises(PermissionError, root.child('~alice').remove)
        return self.assertFailure(
            defer.maybeDeferred(root.createDirectory, 'xyz'), PermissionError)

    def testUserDirPlusJunk(self):
        avatar = SFTPOnlyAvatar('alice', self.tmpdir, self.aliceUserDict, None)
        root = avatar.filesystem.root
        userDir = root.child('~alice')
        self.assertIn('+junk', [name for name, child in userDir.children()])

    def testTeamDirPlusJunk(self):
        avatar = SFTPOnlyAvatar('bob', self.tmpdir, self.bobUserDict, None)
        root = avatar.filesystem.root
        userDir = root.child('~test-team')
        self.assertNotIn('+junk', [name for name, child in userDir.children()])


class UserDirsTestCase(AvatarTestBase):
    def testCreateValidProduct(self):
        # Test creating a product dir.

        class Launchpad:
            test = self
            def fetchProductID(self, productName):
                self.test.assertEqual('mozilla-firefox', productName)
                return defer.succeed(123)
        avatar = SFTPOnlyAvatar('alice', self.tmpdir, self.aliceUserDict,
                                Launchpad())
        root = avatar.filesystem.root
        userDir = root.child('~alice')
        self.assertEqual(
            [name for name, child in userDir.children()], 
            ['.', '..', '+junk'])
        deferred = defer.maybeDeferred(
            userDir.createDirectory, 'mozilla-firefox')
        def cb(result):
            self.assertEqual(
                [name for name, child in userDir.children()], 
                ['.', '..', '+junk', 'mozilla-firefox'])
        deferred.addCallback(cb)
        return deferred

    def testCreateInvalidProduct(self):
        class Launchpad:
            test = self
            def fetchProductID(self, productName):
                self.test.assertEqual('mozilla-firefox', productName)
                # None signals that the product doesn't exist
                return defer.succeed(None)
        avatar = SFTPOnlyAvatar('alice', self.tmpdir, self.aliceUserDict,
                                Launchpad())
        root = avatar.filesystem.root
        userDir = root.child('~alice')

        # We expect PermissionError from a userDir.createDirectory:
        return self.assertFailure(
            defer.maybeDeferred(userDir.createDirectory, 'mozilla-firefox'), 
            PermissionError)

#class TeamDirsTestCase(AvatarTestBase):
#    """Same as UserDirsTestCase, except with a team dir."""
    

class ProductDirsTestCase(AvatarTestBase):
    def testCreateBranch(self):
        class Launchpad:
            test = self
            def fetchProductID(self, productName):
                self.test.assertEqual(productName, 'mozilla-firefox')
                return defer.succeed(123)
            def createBranch(self, userID, productID, branchName):
                self.test.assertEqual(1, userID)
                self.test.assertEqual('123', productID)
                self.test.assertEqual('new-branch', branchName)
                return defer.succeed(0xabcdef12)
        avatar = SFTPOnlyAvatar('alice', self.tmpdir, self.aliceUserDict,
                                Launchpad())
        root = avatar.filesystem.root
        userDir = root.child('~alice')
        deferred = defer.maybeDeferred(
            userDir.createDirectory, 'mozilla-firefox')
        def _cb1(productDirectory):
            return productDirectory.createDirectory('new-branch')
        def _cb2(branchDirectory):
            self.failUnless(isinstance(branchDirectory, SFTPServerBranch))
            self.failUnless(
                branchDirectory.realPath.endswith('ab/cd/ef/12'),
                'branch directory is %r, should end with ab/cd/ef/12'
                % branchDirectory.realPath)
        deferred.addCallback(_cb1).addCallback(_cb2)
        return deferred


    
