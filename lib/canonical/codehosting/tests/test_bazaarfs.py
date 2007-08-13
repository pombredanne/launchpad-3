# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

import os
import unittest

from twisted.internet import defer
from twisted.vfs.ivfs import PermissionError, NotFoundError

from canonical.codehosting.sshserver import LaunchpadAvatar
from canonical.codehosting.bazaarfs import (
    SFTPServerRoot, SFTPServerBranch, SFTPServerProductDir,
    SFTPServerProductDirPlaceholder, NameRestrictedWriteLoggingDirectory)
from canonical.codehosting.tests.helpers import AvatarTestCase


class FakeLaunchpad:
    """Mock RPC interface to Launchpad, used for the tests in this module."""

    def __init__(self, test):
        self.test = test

    def fetchProductID(self, productName):
        """Return a fake product ID.

        If productName is 'mozilla-firefox' return a valid but fake id. If
        productName is 'no-such-product', return None signalling that the
        product was not found.

        If productName is anything else, raises an AssertionError.
        """
        self.test.failUnless(productName in ['mozilla-firefox',
                                             'no-such-product'])
        if productName == 'mozilla-firefox':
            return defer.succeed(123)
        else:
            return defer.succeed(None)

    def createBranch(self, loginID, userName, productName, branchName):
        """Check the given parameters and return a fake branch ID in a
        Deferred.
        """
        self.test.assertEqual('alice', userName)
        self.test.assertEqual('mozilla-firefox', productName)
        self.test.assertEqual('new-branch', branchName)
        return defer.succeed(0xabcdef12)


class TestTopLevelDir(AvatarTestCase):
    def testListDirNoTeams(self):
        # list only user dir + team dirs
        avatar = LaunchpadAvatar(
            'alice', self.tmpdir, self.aliceUserDict, None)
        root = SFTPServerRoot(avatar)
        self.assertEqual(
            [name for name, child in root.children()],
            ['.', '..', '~alice'])

    def testListDirTeams(self):
        # list only user dir + team dirs
        avatar = LaunchpadAvatar(
            'bob', self.tmpdir, self.bobUserDict, None)
        root = SFTPServerRoot(avatar)
        self.assertEqual(
            [name for name, child in root.children()],
            ['.', '..', '~bob', '~test-team'])

    def testAllWriteOpsForbidden(self):
        avatar = LaunchpadAvatar(
            'alice', self.tmpdir, self.aliceUserDict, None)
        root = SFTPServerRoot(avatar)
        self.assertRaises(PermissionError, root.createFile, 'xyz')
        self.assertRaises(PermissionError, root.child('~alice').remove)
        return self.assertFailure(
            defer.maybeDeferred(root.createDirectory, 'xyz'), PermissionError)

    def testUserDirPlusJunk(self):
        avatar = LaunchpadAvatar(
            'alice', self.tmpdir, self.aliceUserDict, None)
        root = avatar.makeFileSystem().root
        userDir = root.child('~alice')
        self.assertIn('+junk', [name for name, child in userDir.children()])

    def testTeamDirPlusJunk(self):
        avatar = LaunchpadAvatar('bob', self.tmpdir, self.bobUserDict, None)
        root = avatar.makeFileSystem().root
        userDir = root.child('~test-team')
        self.assertNotIn('+junk', [name for name, child in userDir.children()])


class UserDirsTestCase(AvatarTestCase):
    def testCreateValidProduct(self):
        # Test creating a product dir.
        avatar = LaunchpadAvatar('alice', self.tmpdir, self.aliceUserDict,
                                 FakeLaunchpad(self))
        root = avatar.makeFileSystem().root
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
        avatar = LaunchpadAvatar('alice', self.tmpdir, self.aliceUserDict,
                                 FakeLaunchpad(self))
        root = avatar.makeFileSystem().root
        userDir = root.child('~alice')

        d = defer.maybeDeferred(userDir.createDirectory, 'no-such-product')

        # We expect PermissionError from a userDir.createDirectory:
        d = self.assertFailure(d, PermissionError)

        # And we check that the message is the one we expected:
        def check_message(exception):
            self.assertEqual(
                str(exception),
                'Directories directly under a user directory must be named '
                'after a project name registered in Launchpad '
                '<https://launchpad.net/>.')

        return d.addCallback(check_message)

    def testInitialBranches(self):
        # Check that already existing branches owned by a user appear as
        # expected.
        self.bobUserDict['initialBranches'] = [
            # bob
            (2, [((1, 'mozilla-firefox'),
                  [(1, 'branch-one'), (2, 'branch-two')]),
                 ((2, 'product-x'), [(3, 'branch-y')])]),
            # test team
            (3, [((3, 'thing'), [(4, 'another-branch')])])]
        avatar = LaunchpadAvatar('bob', self.tmpdir, self.bobUserDict, None)
        root = avatar.makeFileSystem().root

        # The user's dir with have mozilla-firefox, product-x, and also +junk.
        self.assertEqual(
            set([name for name, child in root.child('~bob').children()]),
            set(['.', '..', '+junk', 'mozilla-firefox', 'product-x']))

        # The team dir will have just 'thing'.
        self.assertEqual(
            set([name for name, child in root.child('~test-team').children()]),
            set(['.', '..', 'thing']))


class ProductDirsTestCase(AvatarTestCase):
    def testCreateBranch(self):
        avatar = LaunchpadAvatar('alice', self.tmpdir, self.aliceUserDict,
                                 FakeLaunchpad(self))
        root = avatar.makeFileSystem().root
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
            # The branch directory should be an SFTPServerBranch
            self.failUnless(isinstance(branchDirectory, SFTPServerBranch))

            # Its on disk path should be the branch id split into multiple
            # directory levels
            self.assertEqual(
                os.path.join(self.tmpdir, 'ab/cd/ef/12'),
                branchDirectory.realPath)

            # The directory should exist on the disk.
            self.assert_(os.path.exists(branchDirectory.realPath))
            return branchDirectory

        # Connect the callbacks, and wait for them to run.
        deferred.addCallback(_cb1).addCallback(_cb2)
        return deferred

    def testRmdirBranchDenied(self):
        # Deleting a branch directory should fail with a permission error.

        # Create an empty branch directory
        deferred = self.testCreateBranch()

        # Now attempt to remove the new-branch directory
        def _cb(branchDirectory):
            return branchDirectory.remove()

        # Connect the callbacks, and wait for them to run.
        deferred.addCallback(_cb)
        return self.assertFailure(deferred, PermissionError)


class ProductPlaceholderTestCase(AvatarTestCase):

    def _setUpFilesystem(self):
        avatar = LaunchpadAvatar('alice', self.tmpdir, self.aliceUserDict,
                                 FakeLaunchpad(self))
        return avatar.makeFileSystem()

    def testBranchInPlaceholderNotFound(self):
        # Test that we get a NotFoundError when trying to access
        # non-existant branches for products with no branches.
        filesystem = self._setUpFilesystem()

        # first try a registered product name:
        self.failUnless('mozilla-firefox' not in
                        filesystem.fetch('/~alice').children())
        self.assertRaises(NotFoundError, filesystem.fetch,
                          '/~alice/mozilla-firefox/new-branch/.bzr')

        # now try a non-existant product name:
        self.failUnless('no-such-product' not in
                        filesystem.fetch('/~alice').children())
        self.assertRaises(NotFoundError, filesystem.fetch,
                          '/~alice/no-such-product/new-branch/.bzr')

    def testCreateDirInProductPlaceholder(self):
        # Test that we can create a branch directory under a product
        # placeholder provided the product exists.
        filesystem = self._setUpFilesystem()

        firefox = filesystem.fetch('/~alice/mozilla-firefox')
        self.failUnless(isinstance(firefox, SFTPServerProductDirPlaceholder))
        self.failUnless(not firefox.exists('new-branch'))

        deferred = defer.maybeDeferred(firefox.createDirectory,
                                       'new-branch')

        # Check that the branch directory was created properly
        def _cb(branchdir):
            # The branch directory should be an SFTPServerBranch
            self.failUnless(isinstance(branchdir, SFTPServerBranch))

            # Its on disk path should be the branch id split into multiple
            # directory levels
            self.assertEqual(
                os.path.join(self.tmpdir, 'ab/cd/ef/12'),
                branchdir.realPath)

            # The directory should exist on the disk.
            self.assert_(os.path.exists(branchdir.realPath))
            return branchdir
        deferred.addCallback(_cb)

        # check that the product dir has been filled in
        firefox = filesystem.fetch('/~alice/mozilla-firefox')
        self.failUnless(isinstance(firefox, SFTPServerProductDir))

        # and that the branch is available in that directory
        self.failUnless(firefox.exists('new-branch'))

    def testCreateDirInNonExistantProductPlaceholder(self):
        # Test that we get an error if we try to create a branch
        # inside a product placeholder for a non-existant product.
        filesystem = self._setUpFilesystem()

        noproduct = filesystem.fetch('/~alice/no-such-product')
        self.failUnless(isinstance(noproduct, SFTPServerProductDirPlaceholder))
        return self.assertFailure(defer.maybeDeferred(
            noproduct.createDirectory, 'new-branch'), PermissionError)


class TestSFTPServerBranch(AvatarTestCase):

    def setUp(self):
        AvatarTestCase.setUp(self)
        avatar = LaunchpadAvatar('alice', self.tmpdir, self.aliceUserDict,
                                 FakeLaunchpad(self))
        root = avatar.makeFileSystem().root
        root.setListenerFactory(lambda branch_id: (lambda: None))
        userDir = root.child('~alice')
        d = defer.maybeDeferred(userDir.createDirectory, 'mozilla-firefox')
        d.addCallback(lambda product: product.createDirectory('new-branch'))

        # Store the branch directory
        def _storeServerBranch(branchDirectory):
            self.server_branch = branchDirectory

        return d.addCallback(_storeServerBranch)

    def testCreateBazaarDirectoryWorks(self):
        """Creating a '.bzr' directory underneath a branch directory works."""
        directory = self.server_branch.createDirectory('.bzr')
        self.failUnless(
            isinstance(directory, NameRestrictedWriteLoggingDirectory),
            "%r not instance of _RenameProtectionDecorator (%r)"
            % (directory, type(directory)))

    def testCreateNonBazaarDirectoryFails(self):
        """Creating a non-'.bzr' directory fails.

        This guarantees that users aren't creating directories beneath the
        branch directories and putting branches in those deep directories.
        """
        d = defer.maybeDeferred(self.server_branch.createDirectory, 'foo')
        return self.assertFailure(d, PermissionError)

    def testCreateFileFails(self):
        """Creating a file in a branch fails.

        We only allow Bazaar control directories.
        """
        d = defer.maybeDeferred(self.server_branch.createFile, '.bzr')
        return self.assertFailure(d, PermissionError)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

