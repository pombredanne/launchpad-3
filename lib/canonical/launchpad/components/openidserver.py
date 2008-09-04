# Copyright 2008 Canonical Ltd.  All rights reserved.

"""OpenID adapters and helper objects."""

__metaclass__ = type

__all__ = [
    'OpenIDPersistentIdentity',
    ]

import re

from zope.interface import implements

from canonical.launchpad.layers import OpenIdLayer
from canonical.launchpad.interfaces.openidserver import (
    IOpenIDPersistentIdentity)
from canonical.launchpad.webapp.publisher import get_current_browser_request
from canonical.launchpad.webapp.vhosts import allvhosts


class OpenIDPersistentIdentity:
    """A persistent OpenID identifier for a user."""

    implements(IOpenIDPersistentIdentity)

    def __init__(self, account):
        self.account = account

    # XXX sinzui 2008-09-04 bug=264783:
    # Remove old_openid_identity_url.
    # Rename new_openid_identifier => openid_identifier.
    # Rename new_openid_identity_url => openid_identity_url.
    # Remove OpenIdLayer clause from supportsURL().
    @property
    def new_openid_identifier(self):
        """See `IOpenIDPersistentIdentity`."""
        # The account is very restricted.
        from zope.security.proxy import removeSecurityProxy
        return removeSecurityProxy(self.account).new_openid_identifier

    @property
    def new_openid_identity_url(self):
        """See `IOpenIDPersistentIdentity`."""
        identity_url_root = allvhosts.configs['id'].rooturl
        return identity_url_root + self.new_openid_identifier.encode('ascii')

    @property
    def openid_identifier(self):
        """See `IOpenIDPersistentIdentity`."""
        # The account is very restricted.
        from zope.security.proxy import removeSecurityProxy
        return '+id/' + removeSecurityProxy(self.account).openid_identifier

    @property
    def old_openid_identity_url(self):
        """See `IOpenIDPersistentIdentity`."""
        identity_url_root = allvhosts.configs['openid'].rooturl
        return identity_url_root + self.openid_identifier.encode('ascii')

    @property
    def openid_identity_url(self):
        """See `IOpenIDPersistentIdentity`."""
        request = get_current_browser_request()
        if OpenIdLayer.providedBy(request):
            # Support the old OpenID URL.
            return self.old_openid_identity_url
        return self.new_openid_identity_url

    @staticmethod
    def supportsURL(identity_url):
        """See `IOpenIDPersistentIdentity`."""
        # XXX sinzui 2008-09-04: This should be a condition that checks
        # the current request, to learn which vhost is requested.
        # Return True if the patch can be matched, otherwise False.
        request = get_current_browser_request()
        if OpenIdLayer.providedBy(request):
            identity_url_root = allvhosts.configs['openid'].rooturl
            return identity_url.startswith(identity_url_root + '+id/')
        identity_url_root = allvhosts.configs['id'].rooturl
        identity_url_re = re.compile(r'%s\d\d\d/' % identity_url_root)
        return identity_url_re.match(identity_url) is not None

def account_to_openidpersistentidentity(account):
    """Adapts an `IAccount` into an `IOpenIDPersistentIdentity`."""
    return OpenIDPersistentIdentity(account)

