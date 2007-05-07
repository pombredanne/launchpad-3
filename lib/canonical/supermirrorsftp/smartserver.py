# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Smart server support for the supermirror."""

__metaclass__ = type
__all__ = ['ExecOnlySession']


from zope.interface import implements

from twisted.conch.interfaces import ISession


class ExecOnlySession:
    """Conch session that only allows executing commands."""

    implements(ISession)

    def __init__(self, avatar):
        self.avatar = avatar

    def closed(self):
        """Override me to provide specific cleanup."""

    def eofReceived(self):
        """Override me to provide specific cleanup."""

    def execCommand(self, protocol, command):
        """Override me to implement command execution."""

    def getPty(self, term, windowSize, modes):
        raise NotImplementedError()

    def openShell(self, protocol):
        raise NotImplementedError()

    def windowChanged(self, newWindowSize):
        raise NotImplementedError()
