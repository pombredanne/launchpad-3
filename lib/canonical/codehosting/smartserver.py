# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Smart server support for the supermirror."""

__metaclass__ = type
__all__ = [
    'ExecOnlySession', 'RestrictedExecOnlySession', 'get_bzr_path',
    'launch_smart_server']

import os

from zope.interface import implements

from twisted.conch.interfaces import ISession
from twisted.internet.process import ProcessExitedAlready
from twisted.python import log


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
        executable, arguments = self.getCommandToRun(command)
        log.msg('Running: %r, %r, %r'
                % (executable, arguments, self.environment))
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
        raise NotImplementedError()

    def openShell(self, protocol):
        """See ISession."""
        raise NotImplementedError()

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
            command that will be run. '%(avatarId)s' will be replaced with the
            current avatar's id (generally a username).
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
            raise ForbiddenCommand("Not allowed to execute %r" % (command,))
        return ExecOnlySession.getCommandToRun(
            self, self.executed_command_template
            % {'avatarId': self.avatar.avatarId})


def get_bzr_path():
    import bzrlib
    ROCKETFUEL_ROOT = os.path.dirname(
        os.path.dirname(os.path.dirname(bzrlib.__file__)))
    return ROCKETFUEL_ROOT + '/sourcecode/bzr/bzr'


def launch_smart_server(avatar):
    import sys
    from canonical.codehosting import plugins
    from twisted.internet import reactor

    bzr_plugin_path = os.path.abspath(os.path.dirname(plugins.__file__))
    command = (
        "%(python)s %(bzr)s lp-serve --inet "
        % {'python': sys.executable, 'bzr': get_bzr_path()})

    environment = dict(os.environ)
    environment['BZR_PLUGIN_PATH'] = bzr_plugin_path
    return RestrictedExecOnlySession(
        avatar,
        reactor,
        'bzr serve --inet --directory=/ --allow-writes',
        command + ' %(avatarId)s',
        environment=environment)
