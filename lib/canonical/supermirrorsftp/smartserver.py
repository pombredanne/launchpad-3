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
    def avatarAdapter(klass, avatar):
        from twisted.internet import reactor
        return klass(avatar, reactor)

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
        args = command.split()
        executable, args = args[0], tuple(args[1:])
        self._transport = self.reactor.spawnProcess(protocol, executable, args)

    def getPty(self, term, windowSize, modes):
        raise NotImplementedError()

    def openShell(self, protocol):
        raise NotImplementedError()

    def windowChanged(self, newWindowSize):
        raise NotImplementedError()


class RestrictedExecOnlySession(ExecOnlySession):
    """Conch session that only allows a single command to be executed."""

    def __init__(self, avatar, reactor, allowed_command):
        ExecOnlySession.__init__(self, avatar, reactor)
        self._allowed_command = allowed_command

    @classmethod
    def avatarAdapter(klass, avatar):
        from twisted.internet import reactor
        return klass(avatar, reactor, 'bzr serve --inet /')

    def execCommand(self, protocol, command):
        """If `command` is the allowed command then run the predefined command.

        See `ExecOnlySession.execCommand`.
        """
        if command != self._allowed_command:
            raise ForbiddenCommand("Not allowed to execute %r" % (command,))
        self._transport = self.reactor.spawnProcess(
            protocol, 'bzr', ('launchpad-serve', self.avatar.avatarId))
