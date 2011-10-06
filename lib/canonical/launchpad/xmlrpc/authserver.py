# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Auth-Server XML-RPC API ."""

__metaclass__ = type

__all__ = [
    'AuthServerAPIView',
    ]

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces.authserver import IAuthServer
from canonical.launchpad.webapp import LaunchpadXMLRPCView
from canonical.launchpad.xmlrpc import faults
from lp.registry.interfaces.person import IPersonSet


class AuthServerAPIView(LaunchpadXMLRPCView):
    """See `IAuthServer`."""

    implements(IAuthServer)

    def getUserAndSSHKeys(self, name):
        """See `IAuthServer.getUserAndSSHKeys`."""
        person = getUtility(IPersonSet).getByName(name)
        if person is None:
            return faults.NoSuchPersonWithName(name)
        return {
            'id': person.id,
            'name': person.name,
            'keys': [(key.keytype.title, key.keytext)
                     for key in person.sshkeys],
            }

