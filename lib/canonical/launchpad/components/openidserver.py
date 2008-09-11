# Copyright 2008 Canonical Ltd.  All rights reserved.

"""OpenID adapters and helper objects."""

__metaclass__ = type

__all__ = [
    'get_openid_server_url',
    'get_openid_vhost',
    'OpenIDPersistentIdentity',
    ]

import re

from zope.interface import implements

from canonical.launchpad.layers import OpenIDLayer
from canonical.launchpad.interfaces.openidserver import (
    IOpenIDPersistentIdentity)
from canonical.launchpad.webapp.publisher import get_current_browser_request
from canonical.launchpad.webapp.vhosts import allvhosts


def get_openid_server_url(vhost=None):
    """The OpenID server URL for the current request.

    The default server URL uses the 'id' vhost's root URL. If the `IRequest`
    implements the `OpenIDLayer` layer, the 'openid' vhost is used.

    :return: The OpenID server URL in the form of
        'https://<vhost>.launchpad.net/+openid'
    """
    request = get_current_browser_request()
    if OpenIDLayer.providedBy(request):
        vhost = 'openid'
    else:
        vhost = 'id'
    return allvhosts.configs[vhost].rooturl + '+openid'


def get_openid_vhost():
    """The OpenID server URL for the current request.

    The default server URL uses the 'id' vhost's root URL. If the `IRequest`
    implements the `OpenIDLayer` layer, the 'openid' vhost is used.

    :return: The OpenID server URL in the form of
        'https://<vhost>.launchpad.net/+openid'
    """
    request = get_current_browser_request()
    if OpenIDLayer.providedBy(request):
        return 'openid'
    else:
        return 'id'


class OpenIDPersistentIdentity:
    """A persistent OpenID identifier for a user."""

    implements(IOpenIDPersistentIdentity)

    def __init__(self, account):
        from canonical.launchpad.interfaces.account import IAccount
        assert IAccount.providedBy(account), "FUCKING CALLSITE"
        self.account = account

    # XXX sinzui 2008-09-04 bug=264783:
    # Remove old_openid_identity_url.
    # Rename new_openid_identifier => openid_identifier.
    # Rename new_openid_identity_url => openid_identity_url.
    # Remove OpenIDLayer clause from supportsURL().
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
        token = removeSecurityProxy(self.account).openid_identifier
        if token is None:
            return None
        return '+id/' + token

    @property
    def old_openid_identity_url(self):
        """See `IOpenIDPersistentIdentity`."""
        identity_url_root = allvhosts.configs['openid'].rooturl
        return identity_url_root + self.openid_identifier.encode('ascii')

    @property
    def openid_identity_url(self):
        """See `IOpenIDPersistentIdentity`."""
        request = get_current_browser_request()
        only_old_identifier = (
            self.new_openid_identifier is None
            and self.openid_identifier is not None)
        if only_old_identifier or OpenIDLayer.providedBy(request):
            # Support the old OpenID URL.
            return self.old_openid_identity_url
        return self.new_openid_identity_url

    @property
    def selected_openid_identifier(self):
        """See `IOpenIDPersistentIdentity`."""
        request = get_current_browser_request()
        if OpenIDLayer.providedBy(request):
            return self.openid_identifier
        else:
            return self.new_openid_identifier

    @staticmethod
    def supportsURL(identity_url):
        """See `IOpenIDPersistentIdentity`."""
        request = get_current_browser_request()
        if OpenIDLayer.providedBy(request):
            identity_url_root = allvhosts.configs['openid'].rooturl
            return identity_url.startswith(identity_url_root + '+id')
        identity_url_root = allvhosts.configs['id'].rooturl
        identity_url_re = re.compile(r'%s\d\d\d' % identity_url_root)
        return identity_url_re.match(identity_url) is not None


def account_to_openidpersistentidentity(account):
    """Adapts an `IAccount` into an `IOpenIDPersistentIdentity`."""
    return OpenIDPersistentIdentity(account)

