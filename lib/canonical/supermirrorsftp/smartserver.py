# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Smart server support for the supermirror."""

__metaclass__ = type
__all__ = ['ExecOnlySession', 'RestrictedExecOnlySession']


from zope.interface import implements

from twisted.conch.interfaces import ISession
from twisted.internet.process import ProcessExitedAlready


class ForbiddenCommand(Exception):
    """Raised when a session is asked to execute a forbidden command."""


class ExecOnlySession:
    """Conch session that only allows executing commands."""

    implements(ISession)

    def __init__(self, avatar, reactor):
        self.avatar = avatar
        self.reactor = reactor
        self._transport = None

    @classmethod
    def getAvatarAdapter(klass):
        from twisted.internet import reactor
        return lambda avatar: klass(avatar, reactor)

    def closed(self):
        if self._transport is not None:
            try:
                self._transport.signalProcess('HUP')
            except (OSError, ProcessExitedAlready):
                pass
            self._transport.loseConnection()

    def eofReceived(self):
        if self._transport is not None:
            self._transport.closeStdin()

    def execCommand(self, protocol, command):
        """Executes `command` using `protocol` as the ProcessProtocol.

        :param protocol: a ProcessProtocol, usually SSHSessionProcessProtocol.
        :param command: A whitespace-separated command line. The first token is
        used as the name of the executable, the rest are used as arguments.
        """
        executable, arguments = self.getCommandToRun(command)
        self._transport = self.reactor.spawnProcess(
            protocol, executable, arguments)

    def getCommandToRun(self, command):
        """Return the (executable, args) that will actually be run given
        command. Raise ForbiddenCommand if `command` is forbidden.
        """
        args = command.split()
        return args[0], tuple(args[1:])

    def getPty(self, term, windowSize, modes):
        raise NotImplementedError()

    def openShell(self, protocol):
        raise NotImplementedError()

    def windowChanged(self, newWindowSize):
        raise NotImplementedError()


class RestrictedExecOnlySession(ExecOnlySession):
    """Conch session that only allows a single command to be executed."""

    def __init__(self, avatar, reactor, allowed_command,
                 executed_command_template):
        """Construct a RestrictedExecOnlySession.

        :param avatar: See `ExecOnlySession`.
        :param reactor: See `ExecOnlySession`.
        :param allowed_command: The sole command that can be executed.
        :param executed_command_template: A Python format string for the actual
            command that will be run. '%(avatarId)s' will be replaced with the
            current avatar's id (generally a username).
        """
        ExecOnlySession.__init__(self, avatar, reactor)
        self.allowed_command = allowed_command
        self.executed_command_template = executed_command_template

    @classmethod
    def getAvatarAdapter(klass, allowed_command, executed_command_template):
        from twisted.internet import reactor
        return lambda avatar: klass(avatar, reactor, allowed_command,
                                    executed_command_template)

    def getCommandToRun(self, command):
        if command != self.allowed_command:
            raise ForbiddenCommand("Not allowed to execute %r" % (command,))
        return ExecOnlySession.getCommandToRun(
            self, self.executed_command_template
            % {'avatarId': self.avatar.avatarId})
