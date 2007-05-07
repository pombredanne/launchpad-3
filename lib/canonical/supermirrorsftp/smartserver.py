# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Smart server support for the supermirror."""

__metaclass__ = type
__all__ = ['ExecOnlySession']


from zope.interface import implements

from twisted.conch.interfaces import ISession


class ExecOnlySession:
    """Conch session that only allows executing commands."""

    implements(ISession)

    def __init__(self, avatar, reactor):
        self.avatar = avatar
        self.reactor = reactor

    @classmethod
    def avatarAdapter(klass, avatar):
        from twisted.internet import reactor
        return klass(avatar, reactor)

    def closed(self):
        """Override me to provide specific cleanup."""

    def eofReceived(self):
        """Override me to provide specific cleanup."""

    def execCommand(self, protocol, command):
        """Executes `command` using `protocol` as the ProcessProtocol.

        :param protocol: a ProcessProtocol, usually SSHSessionProcessProtocol.
        :param command: A whitespace-separated command line. The first token is
        used as the name of the executable, the rest are used as arguments.
        """
        args = command.split()
        executable, args = args[0], tuple(args[1:])
        self.reactor.spawnProcess(protocol, executable, args)

    def getPty(self, term, windowSize, modes):
        raise NotImplementedError()

    def openShell(self, protocol):
        raise NotImplementedError()

    def windowChanged(self, newWindowSize):
        raise NotImplementedError()
