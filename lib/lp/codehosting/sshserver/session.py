# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

"""SSH session implementations for the codehosting SSH server."""

__metaclass__ = type
__all__ = [
    'launch_smart_server',
    'PatchedSSHSession',
    ]

import os
import urlparse

from zope.event import notify
from zope.interface import implements

from twisted.conch.interfaces import ISession
from twisted.conch.ssh import channel, session
from twisted.internet.process import ProcessExitedAlready
from twisted.python import log

from canonical.config import config
from lp.codehosting import get_bzr_path
from lp.codehosting.sshserver import accesslog


class PatchedSSHSession(session.SSHSession, object):
    """Session adapter that corrects bugs in Conch.

    This object provides no custom logic for Launchpad, it just addresses some
    simple bugs in the base `session.SSHSession` class that are not yet fixed
    upstream.
    """

    def closeReceived(self):
        # Without this, the client hangs when it's finished transferring.
        # XXX: JonathanLange 2009-01-05: This does not appear to have a
        # corresponding bug in Twisted. We should test that the above comment
        # is indeed correct and then file a bug upstream.
        self.loseConnection()

    def loseConnection(self):
        # XXX: JonathanLange 2008-03-31: This deliberately replaces the
        # implementation of session.SSHSession.loseConnection. The default
        # implementation will try to call loseConnection on the client
        # transport even if it's None. I don't know *why* it is None, so this
        # doesn't necessarily address the root cause.
        # See http://twistedmatrix.com/trac/ticket/2754.
        transport = getattr(self.client, 'transport', None)
        if transport is not None:
            transport.loseConnection()
        # This is called by session.SSHSession.loseConnection. SSHChannel is
        # the base class of SSHSession.
        channel.SSHChannel.loseConnection(self)

    def stopWriting(self):
        """See `session.SSHSession.stopWriting`.

        When the client can't keep up with us, we ask the child process to
        stop giving us data.
        """
        # XXX: MichaelHudson 2008-06-27: Being cagey about whether
        # self.client.transport is entirely paranoia inspired by the comment
        # in `loseConnection` above. It would be good to know if and why it is
        # necessary. See http://twistedmatrix.com/trac/ticket/2754.
        transport = getattr(self.client, 'transport', None)
        if transport is not None:
            # For SFTP connections, 'transport' is actually a _DummyTransport
            # instance. Neither _DummyTransport nor the protocol it wraps
            # (filetransfer.FileTransferServer) support pausing.
            pauseProducing = getattr(transport, 'pauseProducing', None)
            if pauseProducing is not None:
                pauseProducing()

    def startWriting(self):
        """See `session.SSHSession.startWriting`.

        The client is ready for data again, so ask the child to start
        producing data again.
        """
        # XXX: MichaelHudson 2008-06-27: Being cagey about whether
        # self.client.transport is entirely paranoia inspired by the comment
        # in `loseConnection` above. It would be good to know if and why it is
        # necessary. See http://twistedmatrix.com/trac/ticket/2754.
        transport = getattr(self.client, 'transport', None)
        if transport is not None:
            # For SFTP connections, 'transport' is actually a _DummyTransport
            # instance. Neither _DummyTransport nor the protocol it wraps
            # (filetransfer.FileTransferServer) support pausing.
            resumeProducing = getattr(transport, 'resumeProducing', None)
            if resumeProducing is not None:
                resumeProducing()


class ForbiddenCommand(Exception):
    """Raised when a session is asked to execute a forbidden command."""


class ExecOnlySession:
    """Conch session that only allows executing commands."""

    implements(ISession)

    def __init__(self, avatar, reactor, environment=None):
        self.avatar = avatar
        self.reactor = reactor
        self.environment = environment
        self._transport = None

    @classmethod
    def getAvatarAdapter(klass, environment=None):
        from twisted.internet import reactor
        return lambda avatar: klass(avatar, reactor, environment)

    def closed(self):
        """See ISession."""
        if self._transport is not None:
            notify(accesslog.BazaarSSHClosed(self.avatar))
            try:
                self._transport.signalProcess('HUP')
            except (OSError, ProcessExitedAlready):
                pass
            self._transport.loseConnection()

    def eofReceived(self):
        """See ISession."""
        if self._transport is not None:
            self._transport.closeStdin()

    def execCommand(self, protocol, command):
        """Executes `command` using `protocol` as the ProcessProtocol.

        See ISession.

        :param protocol: a ProcessProtocol, usually SSHSessionProcessProtocol.
        :param command: A whitespace-separated command line. The first token is
        used as the name of the executable, the rest are used as arguments.
        """
        try:
            executable, arguments = self.getCommandToRun(command)
        except ForbiddenCommand, e:
            protocol.write(str(e) + '\r\n')
            protocol.loseConnection()
            return
        log.msg('Running: %r, %r, %r'
                % (executable, arguments, self.environment))
        if self._transport is not None:
            log.err(
                "ERROR: %r already running a command on transport %r"
                % (self, self._transport))
        # XXX: JonathanLange 2008-12-23: This is something of an abstraction
        # violation. Apart from this line, this class knows nothing about
        # Bazaar.
        notify(accesslog.BazaarSSHStarted(self.avatar))
        self._transport = self.reactor.spawnProcess(
            protocol, executable, arguments, env=self.environment)

    def getCommandToRun(self, command):
        """Return the command that will actually be run given `command`.

        :param command: A command line to run.
        :return: `(executable, arguments)` where `executable` is the name of an
            executable and arguments is a sequence of command-line arguments
            with the name of the executable as the first value.
        """
        args = command.split()
        return args[0], args

    def getPty(self, term, windowSize, modes):
        """See ISession."""
        # Do nothing, as we don't provide shell access. openShell will get
        # called and handle this error message and disconnect.

    def openShell(self, protocol):
        """See ISession."""
        protocol.write("No shells on this server.\r\n")
        protocol.loseConnection()

    def windowChanged(self, newWindowSize):
        """See ISession."""
        raise NotImplementedError()


class RestrictedExecOnlySession(ExecOnlySession):
    """Conch session that only allows a single command to be executed."""

    def __init__(self, avatar, reactor, allowed_command,
                 executed_command_template, environment=None):
        """Construct a RestrictedExecOnlySession.

        :param avatar: See `ExecOnlySession`.
        :param reactor: See `ExecOnlySession`.
        :param allowed_command: The sole command that can be executed.
        :param executed_command_template: A Python format string for the actual
            command that will be run. '%(user_id)s' will be replaced with the
            'user_id' attribute of the current avatar.
        """
        ExecOnlySession.__init__(self, avatar, reactor, environment)
        self.allowed_command = allowed_command
        self.executed_command_template = executed_command_template

    @classmethod
    def getAvatarAdapter(klass, allowed_command, executed_command_template,
                         environment=None):
        from twisted.internet import reactor
        return lambda avatar: klass(
            avatar, reactor, allowed_command, executed_command_template,
            environment)

    def getCommandToRun(self, command):
        """As in ExecOnlySession, but only allow a particular command.

        :raise ForbiddenCommand: when `command` is not the allowed command.
        """
        if command != self.allowed_command:
            raise ForbiddenCommand("Not allowed to execute %r." % (command,))
        return ExecOnlySession.getCommandToRun(
            self, self.executed_command_template
            % {'user_id': self.avatar.user_id})


def launch_smart_server(avatar):
    import sys
    from twisted.internet import reactor

    command = (
        "%(python)s %(bzr)s lp-serve --inet "
        % {'python': sys.executable, 'bzr': get_bzr_path()})

    environment = dict(os.environ)

    # Extract the hostname from the supermirror root config.
    hostname = urlparse.urlparse(config.codehosting.supermirror_root)[1]
    environment['BZR_EMAIL'] = '%s@%s' % (avatar.username, hostname)
    return RestrictedExecOnlySession(
        avatar,
        reactor,
        'bzr serve --inet --directory=/ --allow-writes',
        command + ' %(user_id)s',
        environment=environment)
