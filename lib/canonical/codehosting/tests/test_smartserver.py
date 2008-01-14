# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Tests for smart server support on the supermirror."""

__metaclass__ = type

import os
import sys
import unittest

from twisted.conch.interfaces import ISession
from twisted.internet.process import ProcessExitedAlready
from twisted.internet.protocol import ProcessProtocol

from canonical.codehosting.sshserver import LaunchpadAvatar
from canonical.codehosting.tests.helpers import AvatarTestCase

from canonical.codehosting import smartserver, plugins


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

    def write(self, data):
        self.log.append(('write', data))


class TestExecOnlySession(AvatarTestCase):
    """Tests for ExecOnlySession.

    Conch delegates responsiblity for executing commands to an object that
    implements ISession. The smart server only needs to handle `execCommand`
    and a couple of other book-keeping methods. The methods that relate to
    running a shell or creating a pseudo-terminal raise NotImplementedErrors.
    """

    def setUp(self):
        AvatarTestCase.setUp(self)
        self.avatar = LaunchpadAvatar(
            'alice', self.tmpdir, self.aliceUserDict, None)
        self.reactor = MockReactor()
        self.session = smartserver.ExecOnlySession(self.avatar, self.reactor)

    def test_getPtyNotImplemented(self):
        # getPTY raises a NotImplementedError. It doesn't matter what we pass
        # it.
        self.assertRaises(NotImplementedError,
                          self.session.getPty, None, None, None)

    def test_openShellNotImplemented(self):
        # openShell closes the connection.
        protocol = MockProcessTransport('bash')
        self.session.openShell(protocol)
        self.assertEqual(protocol.log[-1], ('loseConnection',))

    def test_windowChangedNotImplemented(self):
        # windowChanged raises a NotImplementedError. It doesn't matter what we
        # pass it.
        self.assertRaises(NotImplementedError,
                          self.session.windowChanged, None)

    def test_providesISession(self):
        # ExecOnlySession must provide ISession.
        self.failUnless(ISession.providedBy(self.session),
                        "ExecOnlySession doesn't implement ISession")

    def test_closedDoesNothingWhenNoCommand(self):
        # When no process has been created, 'closed' is a no-op.
        self.assertEqual(None, self.session._transport)
        self.session.closed()
        self.assertEqual(None, self.session._transport)

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

    def test_getCommandToRunSplitsCommandLine(self):
        # getCommandToRun takes a command line and splits it into the name of
        # an executable to run and a sequence of arguments.
        command = 'cat foo bar'
        executable, arguments = self.session.getCommandToRun(command)
        self.assertEqual('cat', executable)
        self.assertEqual(['cat', 'foo', 'bar'], list(arguments))

    def test_execCommandSpawnsProcess(self):
        # ExecOnlySession.execCommand spawns the appropriate process.
        protocol = ProcessProtocol()
        command = 'cat /etc/hostname'
        self.session.execCommand(protocol, command)
        executable, arguments = self.session.getCommandToRun(command)
        self.assertEqual([(protocol, executable, arguments, None, None,
                           None, None, 0, None)],
                         self.reactor.log)

    def test_eofReceivedDoesNothingWhenNoCommand(self):
        # When no process has been created, 'eofReceived' is a no-op.
        self.assertEqual(None, self.session._transport)
        self.session.eofReceived()
        self.assertEqual(None, self.session._transport)

    def test_eofReceivedClosesStdin(self):
        # 'eofReceived' closes standard input when called while a command is
        # running.
        protocol = ProcessProtocol()
        self.session.execCommand(protocol, 'cat /etc/hostname')
        self.session.eofReceived()
        self.assertEqual([('closeStdin',)], self.session._transport.log)

    def test_getAvatarAdapter(self):
        # getAvatarAdapter is a convenience classmethod so that ExecOnlySession
        # can be easily registered as an adapter for Conch avatars.
        from twisted.internet import reactor
        adapter = smartserver.ExecOnlySession.getAvatarAdapter()
        session = adapter(self.avatar)
        self.failUnless(isinstance(session, smartserver.ExecOnlySession),
                        "ISession(avatar) doesn't adapt to ExecOnlySession. "
                        "Got %r instead." % (session,))
        self.assertIdentical(self.avatar, session.avatar)
        self.assertIdentical(reactor, session.reactor)

    def test_environment(self):
        # The environment for the executed process can be specified in the
        # ExecOnlySession constructor.
        session = smartserver.ExecOnlySession(self.avatar, self.reactor,
                                              environment={'FOO': 'BAR'})
        protocol = ProcessProtocol()
        session.execCommand(protocol, 'yes')
        self.assertEqual({'FOO': 'BAR'}, session.environment)
        self.assertEqual(
            [(protocol, 'yes', ['yes'], {'FOO': 'BAR'}, None, None, None, 0,
              None)],
            self.reactor.log)

    def test_environmentInGetAvatarAdapter(self):
        # We can pass the environment into getAvatarAdapter so that it is used
        # when we adapt the session.
        adapter = smartserver.ExecOnlySession.getAvatarAdapter(
            environment={'FOO': 'BAR'})
        session = adapter(self.avatar)
        self.assertEqual({'FOO': 'BAR'}, session.environment)


class TestRestrictedExecOnlySession(AvatarTestCase):
    """Tests for RestrictedExecOnlySession.

    bzr+ssh requests to the code hosting SSH server ask the server to execute a
    particular command: 'bzr serve --inet /'. The SSH server rejects all other
    commands.

    When it receives the expected command, the SSH server doesn't actually
    execute the exact given command. Instead, it executes another pre-defined
    command.
    """

    def setUp(self):
        AvatarTestCase.setUp(self)
        self.avatar = LaunchpadAvatar(
            'alice', self.tmpdir, self.aliceUserDict, None)
        self.reactor = MockReactor()
        self.session = smartserver.RestrictedExecOnlySession(
            self.avatar, self.reactor, 'foo', 'bar baz %(avatarId)s')

    def test_makeRestrictedExecOnlySession(self):
        # A RestrictedExecOnlySession is constructed with an avatar, a reactor
        # and an expected command.
        self.failUnless(
            isinstance(self.session, smartserver.RestrictedExecOnlySession),
            "%r not an instance of smartserver.RestrictedExecOnlySession"
            % (self.session,))
        self.assertEqual(self.avatar, self.session.avatar)
        self.assertEqual(self.reactor, self.session.reactor)
        self.assertEqual('foo', self.session.allowed_command)
        self.assertEqual('bar baz %(avatarId)s',
                         self.session.executed_command_template)

    def test_execCommandRejectsUnauthorizedCommands(self):
        # execCommand rejects all commands except for the command specified in
        # the constructor and closes the connection.

        # Note that Conch doesn't have a well-defined way of rejecting
        # commands: raising any exception from execCommand will do. Here we use
        # an exception type defined in smartserver.py.
        protocol = MockProcessTransport('cat')
        self.assertRaises(smartserver.ForbiddenCommand,
                          self.session.execCommand, protocol, 'cat')
        self.assertEqual(protocol.log[-1], ('loseConnection',))

    def test_getCommandToRunReturnsTemplateCommand(self):
        # When passed the allowed command, getCommandToRun always returns the
        # executable and arguments corresponding to the provided executed
        # command template.
        executable, arguments = self.session.getCommandToRun('foo')
        self.assertEqual('bar', executable)
        self.assertEqual(['bar', 'baz', self.avatar.avatarId], list(arguments))

    def test_getAvatarAdapter(self):
        # getAvatarAdapter is a convenience classmethod so that
        # RestrictedExecOnlySession can be easily registered as an adapter for
        # Conch avatars.
        from twisted.internet import reactor
        adapter = smartserver.RestrictedExecOnlySession.getAvatarAdapter(
            allowed_command='foo', executed_command_template='bar baz')
        session = adapter(self.avatar)
        self.failUnless(
            isinstance(session, smartserver.RestrictedExecOnlySession),
            "ISession(avatar) doesn't adapt to RestrictedExecOnlySession. "
            "Got %r instead." % (session,))
        self.assertIdentical(self.avatar, session.avatar)
        self.assertIdentical(reactor, session.reactor)
        self.assertEqual('foo', session.allowed_command)
        self.assertEqual('bar baz', session.executed_command_template)


class TestSessionIntegration(AvatarTestCase):
    """Tests for how the Conch sessions integrate with the rest of the
    supermirror.
    """

    def setUp(self):
        AvatarTestCase.setUp(self)
        self.avatar = LaunchpadAvatar(
            'alice', self.tmpdir, self.aliceUserDict, None)

    def test_avatarAdaptsToRestrictedExecOnlySession(self):
        # When Conch tries to adapt the supermirror avatar to ISession, it
        # adapts to a RestrictedExecOnlySession. This means that a
        # RestrictedExecOnlySession handles any requests to execute a command.
        session = ISession(self.avatar)
        self.failUnless(
            isinstance(session, smartserver.RestrictedExecOnlySession),
            "ISession(avatar) doesn't adapt to ExecOnlySession. "
            "Got %r instead." % (session,))
        self.assertEqual(
            os.path.abspath(os.path.dirname(plugins.__file__)),
            session.environment['BZR_PLUGIN_PATH'])
        self.assertEqual(
            '%s@bazaar.launchpad.dev' % self.avatar.lpname,
            session.environment['BZR_EMAIL'])

        executable, arguments = session.getCommandToRun(
            'bzr serve --inet --directory=/ --allow-writes')
        self.assertEqual(sys.executable, executable)
        self.assertEqual(
            [sys.executable, smartserver.get_bzr_path(), 'lp-serve', '--inet',
             self.avatar.avatarId],
            list(arguments))
        self.assertRaises(smartserver.ForbiddenCommand,
                          session.getCommandToRun, 'rm -rf /')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
