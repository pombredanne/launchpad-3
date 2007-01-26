# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests that when an SFTP connection ends, the Launchpad XML-RPC service will
be notified of any branches that were written to.
"""

__metaclass__ = type
__all__ = []


import shutil
import tempfile
import unittest

from twisted.conch.ssh import filetransfer
from twisted.internet import defer

from canonical.supermirrorsftp import bazaarfs
from canonical.supermirrorsftp.sftponly import SFTPOnlyAvatar
from canonical.supermirrorsftp.tests.helpers import AvatarTestCase


class TestAvatar(SFTPOnlyAvatar):
    def __init__(self, avatarId, homeDirsRoot, userDict, launchpad):
        SFTPOnlyAvatar.__init__(self, avatarId, homeDirsRoot, userDict,
                                launchpad)
        self.subsystemLookup['sftp'] = self._makeFileTransferServer

    def _makeFileTransferServer(self, data=None, avatar=None):
        self._fileTransferServer = filetransfer.FileTransferServer(
            data=data, avatar=avatar)
        return self._fileTransferServer


class Launchpad:

    def __init__(self):
        self.requests = []

    def createBranch(self, userID, productID, branchName):
        self.requests.append(('createBranch', userID, productID, branchName))
        return defer.succeed(6)

    def fetchProductID(self, productName):
        return defer.succeed(3)

    def requestMirror(self, branchID):
        self.requests.append(('requestMirror', branchID))


class TestPushDoneNotification(AvatarTestCase):

    def create_branch(self, avatar, productID, branchName):
        productDir = avatar.filesystem.fetch(
            '/~%s/%s' % (avatar.avatarId, productID))
        d = defer.maybeDeferred(productDir.createDirectory, branchName)
        return d
    
    def test_no_writes(self):
        launchpad = Launchpad()
        avatar = TestAvatar('alice', self.tmpdir, self.aliceUserDict,
                            launchpad)
        # do nothing -- no writes.
        pass # :)

        # 'connect' and disconnect
        server = avatar._makeFileTransferServer(avatar=avatar)
        server.connectionLost(None)
        self.assertEqual([], launchpad.requests)

    def test_creating_branch_notifies_launchpad(self):
        launchpad = Launchpad()
        avatar = TestAvatar('alice', self.tmpdir, self.aliceUserDict,
                            launchpad)
        # touch a branch
        #   - the client will mkdir ~alice/some-product/some-branch,
        #     so we do the same.
        d = self.create_branch(avatar, 'some-product', 'some-branch')

        def post_create(branchDir):
            branchID = branchDir.branchID
            # check for no events yet
            self.assertEqual(
                [('createBranch', avatar.lpid, '3', 'some-branch')],
                launchpad.requests)
            launchpad.requests = []
            # disconnect
            server = avatar._makeFileTransferServer(avatar=avatar)
            server.connectionLost(None)
            # check for events
            self.assertEqual([('requestMirror', branchID)], launchpad.requests)

        return d.addCallback(post_create)


class WriteLoggingNode(unittest.TestCase):

    def setUp(self):
        testName = self.id().split('.')[-1]
        self.tempDir = tempfile.mkdtemp(prefix=testName)
        self.directory = bazaarfs.WriteLoggingDirectory(self.tempDir)

    def tearDown(self):
        shutil.rmtree(self.tempDir)

    def test_rootWatcher(self):
        # Children of a WriteLoggingDirectory should maintain a reference
        # to the top-level WriteLoggingDirectory.
        self.assertEqual(self.directory, self.directory.rootWatcher)
        self.assertEqual(self.directory,
                         self.directory.createDirectory('foo').rootWatcher)

    def test_childDirFactory(self):
        # childDirFactory should return the same class (child nodes also need
        # to track writes).
        child = self.directory.createDirectory('foo')
        self.assertTrue(isinstance(child, bazaarfs.WriteLoggingDirectory),
                        "Child directory should be same type as parent "
                        "directory.")

    def test_noWrites(self):
        self.assertEqual(self.directory.dirty, False)

    def test_createDirectory(self):
        # creating a directory in a directory is a write
        self.directory.createDirectory('foo')
        self.assertEqual(self.directory.dirty, True)

    def test_createDirectoryInSubdir(self):
        # creating a directory in a subdirectory should dirty the watcher
        subdir = self.directory.createDirectory('foo')
        self.directory.dirty = False
        subdir.createDirectory('bar')
        self.assertEqual(self.directory.dirty, True)

    def test_createFile(self):
        # creating a file in a directory is a write
        self.directory.createFile('foo')
        self.assertEqual(self.directory.dirty, True)

    def test_createFileInSubdir(self):
        # creating a file in a subdirectory should dirty the watcher
        subdir = self.directory.createDirectory('foo')
        self.directory.dirty = False
        subdir.createFile('bar')
        self.assertEqual(self.directory.dirty, True)

    def test_rename(self):
        # renaming a directory is a write
        subdir = self.directory.createDirectory('bar')
        self.directory.dirty = False
        subdir.rename('bar')
        self.assertEqual(self.directory.dirty, True)

    def test_remove(self):
        # removing a directory is a write
        subdir = self.directory.createDirectory('foo')
        self.directory.dirty = False
        subdir.remove()
        self.assertEqual(self.directory.dirty, True)

    #def test_write_to_child_node_dirties_top(self)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

