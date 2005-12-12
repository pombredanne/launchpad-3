
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
        # XXX: all tests that use 'None' for the launchpad interface passed to
        #      SFTPOnlyAvatar should perhaps have a special mock object that
        #      asserts on any getattr, to assert that the lp interface isn't
        #      used for certain ops?
        avatar = SFTPOnlyAvatar('alice', self.tmpdir, self.aliceUserDict, None)
        root = SFTPServerRoot(avatar)
        self.assertEqual(
            [name for name, child in root.children()], 
            ['.', '..', '~alice'])

    def testListDirTeams(self):
        # list only user dir + team dirs
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

    def testInitialBranches(self):
        # Check that already existing branches owned by a user appear as
        # expected.
        initialBranches={
            2: [ # bob
                (1, 'mozilla-firefox', [(1, 'branch-one'), (2, 'branch-two')]),
                (2, 'product-x', [(3, 'branch-y')]),
            ],
            3: [ # test-team
                (3, 'thing', [(4, 'another-branch')]),
            ]
        }
        avatar = SFTPOnlyAvatar('bob', self.tmpdir, self.bobUserDict, None,
                                initialBranches=initialBranches)
        root = avatar.filesystem.root

        # The user's dir with have mozilla-firefox, product-x, and also +junk.
        self.assertEqual(
            set([name for name, child in root.child('~bob').children()]), 
            set(['.', '..', '+junk', 'mozilla-firefox', 'product-x']))

        # The team dir will have just 'thing'.
        self.assertEqual(
            set([name for name, child in root.child('~test-team').children()]),
            set(['.', '..', 'thing']))



#class TeamDirsTestCase(AvatarTestBase):
#    """Same as UserDirsTestCase, except with a team dir."""
    

class ProductDirsTestCase(AvatarTestBase):
    def testCreateBranch(self):
        # Define a mock launchpad RPC object.
        class Launchpad:
            test = self
            def fetchProductID(self, productName):
                # expect fetchProductID('mozilla-firefox')
                self.test.assertEqual(productName, 'mozilla-firefox')
                return defer.succeed(123)
            def createBranch(self, userID, productID, branchName):
                # expect createBranch(1, '123', 'new-branch')
                self.test.assertEqual(1, userID)
                self.test.assertEqual('123', productID)
                self.test.assertEqual('new-branch', branchName)
                return defer.succeed(0xabcdef12)
        avatar = SFTPOnlyAvatar('alice', self.tmpdir, self.aliceUserDict,
                                Launchpad())
        root = avatar.filesystem.root
        userDir = root.child('~alice')

        # First create ~alice/mozilla-firefox.  This will trigger a call to
        # fetchProductID.
        deferred = defer.maybeDeferred(
            userDir.createDirectory, 'mozilla-firefox')

        # Once that's done, we'll create ~alice/mozilla-firefox/new-branch.
        # This triggers a call to createBranch.
        def _cb1(productDirectory):
            return productDirectory.createDirectory('new-branch')

        # Then we'll inspect the resulting directory object
        def _cb2(branchDirectory):
            # the branch directory should be an SFTPServerBranch
            self.failUnless(isinstance(branchDirectory, SFTPServerBranch))

            # its on disk path should be the branch id split into multiple
            # directory levels
            self.assertEqual(
                os.path.join(self.tmpdir, 'ab/cd/ef/12'),
                branchDirectory.realPath)

        # Connect the callbacks, and wait for them to run.
        deferred.addCallback(_cb1).addCallback(_cb2)
        return deferred


