# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Tests for smart server support on the supermirror."""

__metaclass__ = type

import unittest

from twisted.conch.interfaces import ISession
from twisted.internet.process import ProcessExitedAlready
from twisted.internet.protocol import ProcessProtocol

from canonical.supermirrorsftp.sftponly import SFTPOnlyAvatar
from canonical.supermirrorsftp.tests.helpers import AvatarTestCase

from canonical.supermirrorsftp import smartserver


class MockReactor:
    """Mock reactor used to check that ExecOnlySession asks the reactor to
    spawn processes.
    """

    def __init__(self):
        self.log = []

    def spawnProcess(self, protocol, executable, args, env=None, path=None,
                     uid=None, gid=None, usePTY=0, childFDs=None):
        self.log.append((protocol, executable, args, env, path, uid, gid,
                         usePTY, childFDs))
        return MockProcessTransport(executable)


class MockProcessTransport:
    """Mock transport used to fake speaking with child processes that are
    mocked out in tests.
    """

    def __init__(self, executable):
        self._executable = executable
        self.log = []

    def closeStdin(self):
        self.log.append(('closeStdin',))

    def loseConnection(self):
        self.log.append(('loseConnection',))

    def signalProcess(self, signal):
        if self._executable == 'raise-os-error':
            raise OSError()
        if self._executable == 'already-terminated':
            raise ProcessExitedAlready()
        self.log.append(('signalProcess', signal))


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
        self.reactor = MockReactor()
        self.session = smartserver.ExecOnlySession(self.avatar, self.reactor)

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

    def test_closedDoesNothingWhenNoCommand(self):
        # When no process has been created, 'closed' is a no-op.
        self.session.closed()

    def test_closedTerminatesProcessAndDisconnects(self):
        # ExecOnlySession provides a 'closed' method that is generally
        # responsible for killing the child process and cleaning things up.
        # From the outside, it just looks like a successful no-op. From the
        # inside, it tells the process transport to end the connection between
        # the SSH server and the child process.
        protocol = ProcessProtocol()
        self.session.execCommand(protocol, 'cat /etc/hostname')
        self.session.closed()
        self.assertEqual(
            [('signalProcess', 'HUP'), ('loseConnection',)],
            self.session._transport.log)

    def test_closedDisconnectsIfProcessCantBeTerminated(self):
        # 'closed' still calls 'loseConnection' on the transport, even if the
        # OS raises an error when we try to SIGHUP the process.
        protocol = ProcessProtocol()
        # MockTransport will raise an OSError on signalProcess if the executed
        # command is 'raise-os-error'.
        self.session.execCommand(protocol, 'raise-os-error')
        self.session.closed()
        self.assertEqual(
            [('loseConnection',)],
            self.session._transport.log)

    def test_closedDisconnectsIfProcessAlreadyTerminated(self):
        # 'closed' still calls 'loseConnection' on the transport, even if the
        # process is already terminated
        protocol = ProcessProtocol()
        # MockTransport will raise a ProcessExitedAlready on signalProcess if
        # the executed command is 'already-terminated'.
        self.session.execCommand(protocol, 'already-terminated')
        self.session.closed()
        self.assertEqual([('loseConnection',)], self.session._transport.log)

    def test_execCommandSpawnsProcess(self):
        # ExecOnlySession.execCommand spawns a process.
        protocol = ProcessProtocol()
        self.session.execCommand(protocol, 'cat /etc/hostname')
        self.assertEqual([(protocol, 'cat', ('/etc/hostname',), None, None,
                           None, None, 0, None)],
                         self.reactor.log)

    def test_eofReceivedDoesNothingWhenNoCommand(self):
        # When no process has been created, 'eofReceived' is a no-op.
        self.session.eofReceived()

    def test_eofReceivedClosesStdin(self):
        # 'eofReceived' closes standard input when called while a command is
        # running.
        protocol = ProcessProtocol()
        self.session.execCommand(protocol, 'cat /etc/hostname')
        self.session.eofReceived()
        self.assertEqual([('closeStdin',)], self.session._transport.log)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
