# Copyright 2008 Canonical Ltd.  All rights reserved.

"""OpenID adapters and helper objects."""

__metaclass__ = type

__all__ = [
    'OpenIDPersistentIdentity',
    ]


from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces.openidserver import (
    IOpenIDPersistentIdentity)
from canonical.launchpad.interfaces.person import IPersonSet
from canonical.launchpad.webapp.vhosts import allvhosts


class OpenIDPersistentIdentity:
    """A persistent OpenID identifier for a user."""

    implements(IOpenIDPersistentIdentity)

    def __init__(self, account):
        self.account = account
        self.person = getUtility(IPersonSet).getByAccount(self.account)

    @property
    def openid_identifier(self):
        """See `IOpenIDPersistentIdentity`."""
        # The account is very restricted
        from zope.security.proxy import removeSecurityProxy
        return '+id/' + removeSecurityProxy(self.account).openid_identifier

    @property
    def displayname(self):
        """See `IOpenIDPersistentIdentity`."""
        # The account is very restricted
        from zope.security.proxy import removeSecurityProxy
        return removeSecurityProxy(self.account).displayname

    @property
    def openid_identity_url(self):
        """See `IOpenIDPersistentIdentity`."""
        identity_url_root = allvhosts.configs['openid'].rooturl
        return identity_url_root + self.openid_identifier.encode('ascii')

    @staticmethod
    def supportsURL(identity_url):
        """See `IOpenIDPersistentIdentity`."""
        # XXX sinzui 2008-07-21: This method should also check the old URL
        # if it exists.
        identity_url_root = allvhosts.configs['openid'].rooturl
        return identity_url.startswith(identity_url_root + '+id/')
