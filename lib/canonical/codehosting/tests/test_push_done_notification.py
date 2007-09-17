# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests that when an SFTP connection ends, the Launchpad XML-RPC service will
be notified of any branches that were written to.
"""

__metaclass__ = type
__all__ = []


import logging
import os
import shutil
import tempfile
import unittest

from twisted.internet import defer

from canonical.codehosting import bazaarfs
from canonical.codehosting.sshserver import (
    BazaarFileTransferServer, LaunchpadAvatar)
from canonical.codehosting.tests.helpers import AvatarTestCase


class Launchpad:

    def __init__(self):
        self.requests = []

    def createBranch(self, loginID, userName, productName, branchName):
        self.requests.append(
            ('createBranch', loginID, userName, productName, branchName))
        return defer.succeed(6)

    def fetchProductID(self, productName):
        return defer.succeed(3)

    def requestMirror(self, branchID):
        self.requests.append(('requestMirror', branchID))
        return defer.succeed(None)


class TestPushDoneNotification(AvatarTestCase):

    def setUp(self):
        AvatarTestCase.setUp(self)
        self.launchpad = Launchpad()
        self.avatar = LaunchpadAvatar('alice', self.tmpdir, self.aliceUserDict,
                                     self.launchpad)
        self.server = self.avatar.lookupSubsystem('sftp', None)
        self.filesystem = self.server.client.filesystem

    def create_branch(self, avatar, productID, branchName):
        productDir = self.filesystem.fetch(
            '/~%s/%s' % (avatar.avatarId, productID))
        d = defer.maybeDeferred(productDir.createDirectory, branchName)
        return d

    def test_no_writes(self):
        # 'connect' and disconnect
        self.server.connectionLost(None)
        self.assertEqual([], self.launchpad.requests)

    def fake_listener_factory(self, branchID):
        def func():
            self.called = branchID
        return func

    def test_branch_dir_gets_listener_factory_from_root(self):
        self.filesystem.root.setListenerFactory(self.fake_listener_factory)
        d = self.create_branch(self.avatar, 'some-product', 'some-branch')
        self.called = None
        def post_create(branchDir):
            # dirty the branch
            branchDir.createDirectory('.bzr')
            self.assertEqual(self.called, branchDir.branchID)
        return d.addCallback(post_create)

    def test_creating_branch_notifies_launchpad(self):
        d = self.create_branch(self.avatar, 'some-product', 'some-branch')

        def post_create(branchDir):
            branchID = branchDir.branchID
            # check for no events yet
            self.assertEqual(
                [('createBranch', self.avatar.lpname, self.avatar.lpname,
                  'some-product', 'some-branch')],
                self.launchpad.requests)
            self.launchpad.requests = []
            # dirty it
            branchDir.createDirectory('.bzr')
            # disconnect
            self.server.connectionLost(None)
            # check for events
            self.assertEqual([('requestMirror', branchID)],
                             self.launchpad.requests)

        return d.addCallback(post_create)


class WriteLoggingDirectory(unittest.TestCase):

    def setUp(self):
        testName = self.id().split('.')[-1]
        self.dirty = False
        self.tempDir = tempfile.mkdtemp(prefix=testName)
        self.directory = bazaarfs.WriteLoggingDirectory(
            self.flagAsDirty, self.tempDir, logging.getLogger())

    def tearDown(self):
        shutil.rmtree(self.tempDir)

    def flagAsDirty(self):
        self.dirty = True

    def test_listener(self):
        # Children of a WriteLoggingDirectory should maintain a reference
        # to the top-level WriteLoggingDirectory.
        # XXX jml 2007-02-15: Whitebox test
        self.assertEqual(self.flagAsDirty, self.directory._flagAsDirty)
        self.assertEqual(self.flagAsDirty,
                         self.directory.createDirectory('foo')._flagAsDirty)

    def test_childDirFactory(self):
        # childDirFactory should return the same class (child nodes also need
        # to track writes).
        child = self.directory.createDirectory('foo')
        self.assertTrue(isinstance(child, bazaarfs.WriteLoggingDirectory),
                        "Child directory should be same type as parent "
                        "directory.")

    def test_noWrites(self):
        self.assertEqual(self.dirty, False)

    def test_createDirectory(self):
        # creating a directory in a directory is a write
        self.directory.createDirectory('foo')
        self.assertEqual(self.dirty, True)

    def test_createDirectoryInSubdir(self):
        # creating a directory in a subdirectory should dirty the watcher
        subdir = self.directory.createDirectory('foo')
        self.directory.dirty = False
        subdir.createDirectory('bar')
        self.assertEqual(self.dirty, True)

    def test_createFile(self):
        # creating a file in a directory is a write
        self.directory.createFile('foo')
        self.assertEqual(self.dirty, True)

    def test_createFileInSubdir(self):
        # creating a file in a subdirectory should dirty the watcher
        subdir = self.directory.createDirectory('foo')
        self.directory.dirty = False
        subdir.createFile('bar')
        self.assertEqual(self.dirty, True)

    def test_rename(self):
        # renaming a directory is a write
        subdir = self.directory.createDirectory('bar')
        self.directory.dirty = False
        subdir.rename('baz')
        self.assertEqual(self.dirty, True)

    def test_remove(self):
        # removing a directory is a write
        subdir = self.directory.createDirectory('foo')
        self.directory.dirty = False
        subdir.remove()
        self.assertEqual(self.dirty, True)


class BazaarFileTransferServerTests(AvatarTestCase):

    def test_branchDirty(self):
        launchpad = Launchpad()
        avatar = LaunchpadAvatar('alice', self.tmpdir, self.aliceUserDict,
                                launchpad)
        server = BazaarFileTransferServer(avatar=avatar)
        server.branchDirtied(1234)
        server.branchDirtied(2357)
        server.sendMirrorRequests()
        self.assertEqual([('requestMirror', 1234), ('requestMirror', 2357)],
                         sorted(launchpad.requests))

    def test_branchDirtyDuplicate(self):
        launchpad = Launchpad()
        avatar = LaunchpadAvatar('alice', self.tmpdir, self.aliceUserDict,
                                 launchpad)
        server = BazaarFileTransferServer(avatar=avatar)
        server.branchDirtied(1234)
        server.branchDirtied(1234)
        server.sendMirrorRequests()
        self.assertEqual([('requestMirror', 1234)], launchpad.requests)


def test_suite():
    return unittest.TestSuite()
    return unittest.TestLoader().loadTestsFromName(__name__)
