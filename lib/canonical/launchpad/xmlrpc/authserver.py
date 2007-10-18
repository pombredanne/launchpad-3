# Copyright 2007 Canonical Ltd., all rights reserved.

"""Legacy Auth-Server XML-RPC API ."""

__metaclass__ = type

__all__ = [
    'AuthServerAPIView',
    ]

from zope.interface import implements

from canonical.authserver.interfaces import IUserDetailsStorageV2
from canonical.launchpad.webapp import LaunchpadXMLRPCView


class AuthServerAPIView(LaunchpadXMLRPCView):
    """The XMLRPC API provided by the old AuthServer and used by the wikis."""
    implements(IUserDetailsStorageV2)

    def getUser(self, loginID):
        """See `IUserDetailsStorageV2`."""

    def authUser(self, loginID, password):
        """See `IUserDetailsStorageV2`."""

    def getSSHKeys(self, archiveName):
        """See `IUserDetailsStorageV2`."""
