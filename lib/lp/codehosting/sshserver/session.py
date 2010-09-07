# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""SSH session implementations for the codehosting SSH server."""

__metaclass__ = type
__all__ = [
    'launch_smart_server',
    ]

import os
import socket
import urlparse

from zope.event import notify
from zope.interfaces import implements

from twisted.internet.interfaces import IProcessTransport
from twisted.internet.process import ProcessExitedAlready
from twisted.python import log

from canonical.config import config
from lp.codehosting import get_bzr_path
from lp.services.sshserver.events import AvatarEvent
from lp.services.sshserver.session import DoNothingSession


class BazaarSSHStarted(AvatarEvent):

    template = '[%(session_id)s] %(username)s started bzr+ssh session.'


class BazaarSSHClosed(AvatarEvent):

    template = '[%(session_id)s] %(username)s closed bzr+ssh session.'


class ForbiddenCommand(Exception):
    """Raised when a session is asked to execute a forbidden command."""


class ForkedProcessTransport(object):
    # I assume we don't need to do 'implements(IProcessProtocol)' since the
    # base class already does this.

    implements(IProcessTransport)

    def sendMessageToService(self, message):
        """Send a message to the Forking service and get the response"""
        # TODO: Config entries for what port this will be found in?
        DEFAULT_SERVICE_PORT = 4156
        addrs = socket.getaddrinfo('127.0.0.1', DEFAULT_SERVICE_PORT,
            socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_PASSIVE)
        (family, socktype, proto, canonname, sockaddr) = addrs[0]
        client_sock = socket.socket(family, socktype, proto)
        # TODO: How do we do logging in this codebase?
        try:
            client_sock.connect(sockaddr)
            client_sock.sendall(msg)
            # We define the requests to be no bigger than 1kB. (For now)
            response = client_sock.recv(1024)
        except socket.error, e:
            # TODO: What exceptions should be raised?
            raise RuntimeError('Failed to connect: %s' % (e,))
        if response.startswith("FAILURE"):
            raise RuntimeError('Failed to send message: %r' % (response,))
        return response

    @classmethod
    def requestFork(cls, command):
        """Request that the Forking service fork and run this command."""
        response = self.sendMessageToService('fork %s' % (command,))
        # The response is the path to the file handles, and we've explicitly
        # checked for FAILURE already.
        path = response.strip()
        stdin_path = os.path.join(path, 'stdin')
        stdout_path = os.path.join(path, 'stdout')
        stderr_path = os.path.join(path, 'stderr')

class ExecOnlySession(DoNothingSession):
    """Conch session that only allows executing commands."""

    def __init__(self, avatar, reactor, environment=None):
        super(ExecOnlySession, self).__init__(avatar)
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
            # XXX: JonathanLange 2010-04-15: This is something of an
            # abstraction violation. Apart from this line and its twin, this
            # class knows nothing about Bazaar.
            notify(BazaarSSHClosed(self.avatar))
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
        # XXX: What do do with the protocol argument? It implements
        #      IProcessProtocol, which is how the process gets spawned, but we
        #      are intentionally overriding that. Are we supposed to be
        #      implementing a custom IProcessProtocol, and
        #      installing/registering that higher up?
        try:
            executable, arguments = self.getCommandToRun(command)
        except ForbiddenCommand, e:
            self.errorWithMessage(protocol, str(e) + '\r\n')
            return
        log.msg('Running: %r, %r, %r'
                % (executable, arguments, self.environment))
        if self._transport is not None:
            log.err(
                "ERROR: %r already running a command on transport %r"
                % (self, self._transport))
        # XXX: JonathanLange 2008-12-23: This is something of an abstraction
        # violation. Apart from this line and its twin, this class knows
        # nothing about Bazaar.
        notify(BazaarSSHStarted(self.avatar))
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
    from twisted.internet import reactor

    command = (
        "lp-serve --inet %(user_id)s"
        )

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
