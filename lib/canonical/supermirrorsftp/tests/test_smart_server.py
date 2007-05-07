# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Tests for smart server support on the supermirror."""

__metaclass__ = type

import unittest

from twisted.conch.interfaces import ISession
from twisted.internet.protocol import ProcessProtocol

from canonical.supermirrorsftp.sftponly import SFTPOnlyAvatar
from canonical.supermirrorsftp.tests.helpers import AvatarTestCase

from canonical.supermirrorsftp import smartserver


class TestExecOnlySession(AvatarTestCase):
    """Tests for ExecOnlySession.

    Conch delegates responsiblity for executing commands to an object that
    implements ISession. The smart server only needs to handle `execCommand`
    and a couple of other book-keeping methods. The methods that relate to
    running a shell or creating a pseudo-terminal raise NotImplementedErrors.
    """

    def setUp(self):
        AvatarTestCase.setUp(self)
        self.avatar = SFTPOnlyAvatar(
            'alice', self.tmpdir, self.aliceUserDict, None)
        self.session = smartserver.ExecOnlySession(self.avatar)

    def test_getPtyNotImplemented(self):
        # getPTY raises a NotImplementedError. It doesn't matter what we pass
        # it.
        self.assertRaises(NotImplementedError,
                          self.session.getPty, None, None, None)

    def test_openShellNotImplemented(self):
        # execCommand raises a NotImplementedError. It doesn't matter what we
        # pass it.
        self.assertRaises(NotImplementedError,
                          self.session.openShell, None)

    def test_windowChangedNotImplemented(self):
        # windowChanged raises a NotImplementedError. It doesn't matter what we
        # pass it.
        self.assertRaises(NotImplementedError,
                          self.session.windowChanged, None)

    def test_providesISession(self):
        # ExecOnlySession must provide ISession.
        self.failUnless(ISession.implementedBy(smartserver.ExecOnlySession),
                        "ExecOnlySession doesn't implement ISession")

    def test_avatarAdaptsToExecOnlySession(self):
        # When Conch tries to adapt the supermirror avatar to ISession, it
        # adapts to an ExecOnlySession. This means that an ExecOnlySession
        # handles any requests to execute a command.
        session = ISession(self.avatar)
        self.failUnless(isinstance(session, smartserver.ExecOnlySession),
                        "ISession(avatar) doesn't adapt to ExecOnlySession. "
                        "Got %r instead." % (session,))
        self.assertIdentical(self.avatar, session.avatar)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
