# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

import os
import unittest

from twisted.internet import defer
from twisted.vfs.ivfs import PermissionError, NotFoundError

from canonical.supermirrorsftp.sftponly import SFTPOnlyAvatar
from canonical.supermirrorsftp.bazaarfs import (
    SFTPServerRoot, SFTPServerBranch, SFTPServerProductDir,
    SFTPServerProductDirPlaceholder)
from canonical.supermirrorsftp.tests.helpers import AvatarTestCase


class TestTopLevelDir(AvatarTestCase):
    def testListDirNoTeams(self):
        # list only user dir + team dirs
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


class UserDirsTestCase(AvatarTestCase):
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
        self.bobUserDict['teams'][0]['initialBranches'] = [ # bob
            (1, 'mozilla-firefox', [(1, 'branch-one'), (2, 'branch-two')]),
            (2, 'product-x', [(3, 'branch-y')]),
        ]
        self.bobUserDict['teams'][1]['initialBranches'] = [ # test-team
            (3, 'thing', [(4, 'another-branch')]),
        ]
        avatar = SFTPOnlyAvatar('bob', self.tmpdir, self.bobUserDict, None)
        root = avatar.filesystem.root

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
        # XXX - factor this out into a common Launchpad utility class
        # jml, 2007-01-26
        class Launchpad:
            test = self
            def fetchProductID(self, productName):
                # expect fetchProductID('mozilla-firefox')
                self.test.failUnless(productName in ['mozilla-firefox',
                                                     'no-such-product'])
                if productName == 'mozilla-firefox':
                    return defer.succeed(123)
                else:
                    # None is returned if the product could not be looked up
                    return defer.succeed(None)

            def createBranch(self, userID, productID, branchName):
                # expect createBranch(1, '123', 'new-branch')
                self.test.assertEqual(1, userID)
                self.test.assertEqual('123', productID)
                self.test.assertEqual('new-branch', branchName)
                return defer.succeed(0xabcdef12)

        avatar = SFTPOnlyAvatar('alice', self.tmpdir, self.aliceUserDict,
                                Launchpad())
        return avatar.filesystem

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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

