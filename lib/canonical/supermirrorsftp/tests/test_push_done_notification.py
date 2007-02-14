# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests that when an SFTP connection ends, the Launchpad XML-RPC service will
be notified of any branches that were written to.
"""

__metaclass__ = type
__all__ = []


import unittest

from twisted.conch.ssh import filetransfer

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


class TestPushDoneNotification(AvatarTestCase):
    
    def test_no_writes(self):
        class Launchpad:
            requestedMirror = False
            def requestMirror(self, branchID):
                self.requestedMirror = True

        launchpad = Launchpad()
        avatar = TestAvatar('alice', self.tmpdir, self.aliceUserDict,
                            launchpad)
        # do nothing -- no writes.
        pass # :)

        # 'connect' and disconnect
        avatar._makeFileTransferServer(avatar=avatar)
        avatar._fileTransferServer.connectionLost(None)
        self.failIf(launchpad.requestedMirror,
                    "No writes, but requestMirror called.")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

