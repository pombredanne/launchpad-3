# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""SSH session implementations for the codehosting SSH server."""

__metaclass__ = type
__all__ = [
    'launch_smart_server',
    ]

import os
import urlparse

from zope.event import notify

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
        "%(root)s/bin/py %(bzr)s lp-serve --inet "
        % {'root': config.root, 'bzr': get_bzr_path()})

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
