# Copyright 2009-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Auth-Server XML-RPC API ."""

__metaclass__ = type

__all__ = [
    'AuthServerApplication',
    'AuthServerAPIView',
    ]

from pymacaroons import Macaroon
from storm.sqlobject import SQLObjectNotFound
from zope.component import (
    ComponentLookupError,
    getUtility,
    )
from zope.interface import implementer
from zope.security.proxy import removeSecurityProxy

from lp.registry.interfaces.person import IPersonSet
from lp.services.authserver.interfaces import (
    IAuthServer,
    IAuthServerApplication,
    )
from lp.services.librarian.interfaces import ILibraryFileAliasSet
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

    def issueMacaroon(self, issuer_name, context):
        """See `IAuthServer.issueMacaroon`."""
        try:
            issuer = getUtility(IMacaroonIssuer, issuer_name)
        except ComponentLookupError:
            return faults.PermissionDenied()
        # Only permit issuers that have been specifically designed for use
        # with the authserver: they must need to be issued by parts of
        # Launchpad other than appservers but be verified by appservers,
        # they must take parameters that can be passed over XML-RPC, and
        # they must issue macaroons with carefully-designed constraints to
        # minimise privilege-escalation attacks.
        if not issuer.issuable_via_authserver:
            return faults.PermissionDenied()
        try:
            # issueMacaroon isn't normally public, but we clearly need it
            # here.
            macaroon = removeSecurityProxy(issuer).issueMacaroon(context)
        except ValueError:
            return faults.PermissionDenied()
        return macaroon.serialize()

    def verifyMacaroon(self, macaroon_raw, context_type, context):
        """See `IAuthServer.verifyMacaroon`."""
        try:
            macaroon = Macaroon.deserialize(macaroon_raw)
        # XXX cjwatson 2019-04-23: Restrict exceptions once
        # https://github.com/ecordell/pymacaroons/issues/50 is fixed.
        except Exception:
            return faults.Unauthorized()
        try:
            issuer = getUtility(IMacaroonIssuer, macaroon.identifier)
        except ComponentLookupError:
            return faults.Unauthorized()
        # The context is plain data, since we can't pass general objects over
        # the XML-RPC interface.  Look it up so that we can verify it.
        if context_type == 'LibraryFileAlias':
            # The context is a `LibraryFileAlias` ID.
            try:
                lfa = getUtility(ILibraryFileAliasSet)[context]
            except SQLObjectNotFound:
                return faults.Unauthorized()
        else:
            return faults.Unauthorized()
        if not issuer.verifyMacaroon(macaroon, lfa):
            return faults.Unauthorized()
        return True


@implementer(IAuthServerApplication)
class AuthServerApplication:
    """AuthServer End-Point."""

    title = "Auth Server"
