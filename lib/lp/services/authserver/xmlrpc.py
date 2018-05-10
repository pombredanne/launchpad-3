# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Auth-Server XML-RPC API ."""

__metaclass__ = type

__all__ = [
    'AuthServerApplication',
    'AuthServerAPIView',
    ]

from pymacaroons import Macaroon
from zope.component import (
    ComponentLookupError,
    getUtility,
    )
from zope.interface import implementer

from lp.registry.interfaces.person import IPersonSet
from lp.services.authserver.interfaces import (
    IAuthServer,
    IAuthServerApplication,
    )
from lp.services.macaroons.interfaces import IMacaroonIssuer
from lp.services.webapp import LaunchpadXMLRPCView
from lp.xmlrpc import faults


@implementer(IAuthServer)
class AuthServerAPIView(LaunchpadXMLRPCView):
    """See `IAuthServer`."""

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

    def verifyMacaroon(self, macaroon_raw, context):
        """See `IAuthServer.verifyMacaroon`."""
        try:
            macaroon = Macaroon.deserialize(macaroon_raw)
        except Exception:
            return faults.Unauthorized()
        try:
            issuer = getUtility(IMacaroonIssuer, macaroon.identifier)
        except ComponentLookupError:
            return faults.Unauthorized()
        if not issuer.verifyMacaroon(macaroon, context):
            return faults.Unauthorized()
        return True


@implementer(IAuthServerApplication)
class AuthServerApplication:
    """AuthServer End-Point."""

    title = "Auth Server"
