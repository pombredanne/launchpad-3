# Copyright 2008-2009 Canonical Ltd.  All rights reserved.

"""OpenID adapters."""

__metaclass__ = type

__all__ = [
    'OpenIDPersistentIdentity',
    ]

from zope.component import adapter, adapts
from zope.interface import implementer, implements
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.account import IAccount
from canonical.launchpad.webapp.vhosts import allvhosts
from lp.services.openid.interfaces.openid import IOpenIDPersistentIdentity
from lp.registry.interfaces.person import IPerson


class OpenIDPersistentIdentity:
    """A persistent OpenID identifier for a user."""

    adapts(IAccount)
    implements(IOpenIDPersistentIdentity)

    def __init__(self, account):
        self.account = account

    @property
    def openid_identity_url(self):
        """See `IOpenIDPersistentIdentity`."""
        identity_root_url = allvhosts.configs['openid'].rooturl
        return identity_root_url + self.openid_identifier.encode('ascii')

    @property
    def openid_identifier(self):
        """See `IOpenIDPersistentIdentity`."""
        # The account is very restricted.
        token = removeSecurityProxy(self.account).openid_identifier
        if token is None:
            return None
        return '+id/' + token


@adapter(IPerson)
@implementer(IOpenIDPersistentIdentity)
def person_to_openidpersistentidentity(person):
    """Adapts an `IPerson` into an `IOpenIDPersistentIdentity`."""
    return OpenIDPersistentIdentity(person.account)
