# Copyright 2008 Canonical Ltd.  All rights reserved.

"""OpenID adapters and helper objects."""

__metaclass__ = type

__all__ = [
    'OpenIDPersistentIdentity',
    'CurrentOpenIDEndPoint',
    ]

import re

from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.layers import OpenIDLayer
from canonical.launchpad.interfaces.openidserver import (
    IOpenIDPersistentIdentity)
from canonical.launchpad.webapp.publisher import get_current_browser_request
from canonical.launchpad.webapp.vhosts import allvhosts


class CurrentOpenIDEndPoint:
    """A utility for working with multiple OpenID End Points."""

    @staticmethod
    def getVHost():
        """The name of the vhost for the current request."""
        request = get_current_browser_request()
        if OpenIDLayer.providedBy(request):
            return 'openid'
        else:
            return 'id'

    @staticmethod
    def getRootURL(vhost=None):
        """The OpenID root URL for the current request.

        :param vhost: The preferred vhost configuration to use, otherwise
            use the vhost associated with the current request.
        """
        if vhost is None:
            vhost = CurrentOpenIDEndPoint.getVHost()
        return allvhosts.configs[vhost].rooturl

    @staticmethod
    def getServiceURL(vhost=None):
        """The OpenID server URL (/+openid) for the current request.

        :param vhost: The preferred vhost configuration to use, otherwise
            use the vhost associated with the current request.
        """
        return CurrentOpenIDEndPoint.getRootURL(vhost=vhost) + '+openid'

    @staticmethod
    def supportsURL(identity_url):
        """Does the OpenID current vhost support the identity_url?"""
        if CurrentOpenIDEndPoint.isRequestForOldVHost():
            root_url = CurrentOpenIDEndPoint.getRootURL(vhost='openid')
            return identity_url.startswith(root_url + '+id')
        root_url = CurrentOpenIDEndPoint.getRootURL(vhost='id')
        identity_url_re = re.compile(r'%s\d\d\d' % root_url)
        return identity_url_re.match(identity_url) is not None

    @staticmethod
    def isRequestForOldVHost():
        """Is the request for the old 'openid' vhost."""
        return CurrentOpenIDEndPoint.getVHost() == 'openid'


class OpenIDPersistentIdentity:
    """A persistent OpenID identifier for a user."""

    implements(IOpenIDPersistentIdentity)

    def __init__(self, account):
        self.account = account

    # XXX sinzui 2008-09-04 bug=264783:
    # Remove old_openid_identifier and old_openid_identity_url.
    # Rename new_openid_identifier => openid_identifier.
    # Rename new_openid_identity_url => openid_identity_url.
    @property
    def new_openid_identifier(self):
        """See `IOpenIDPersistentIdentity`."""
        # The account is very restricted.
        return removeSecurityProxy(self.account).new_openid_identifier

    @property
    def new_openid_identity_url(self):
        """See `IOpenIDPersistentIdentity`."""
        identity_root_url = CurrentOpenIDEndPoint.getRootURL('id')
        return identity_root_url + self.new_openid_identifier.encode('ascii')

    @property
    def old_openid_identifier(self):
        """See `IOpenIDPersistentIdentity`."""
        # The account is very restricted.
        token = removeSecurityProxy(self.account).openid_identifier
        if token is None:
            return None
        return '+id/' + token

    @property
    def old_openid_identity_url(self):
        """See `IOpenIDPersistentIdentity`."""
        identity_root_url = CurrentOpenIDEndPoint.getRootURL('openid')
        return identity_root_url + self.old_openid_identifier.encode('ascii')

    @property
    def openid_identity_url(self):
        """See `IOpenIDPersistentIdentity`."""
        only_old_identifier = (
            self.new_openid_identifier is None
            and self.old_openid_identifier is not None)
        if (only_old_identifier
            or CurrentOpenIDEndPoint.isRequestForOldVHost()):
            return self.old_openid_identity_url
        else:
            return self.new_openid_identity_url

    @property
    def openid_identifier(self):
        """See `IOpenIDPersistentIdentity`."""
        if CurrentOpenIDEndPoint.isRequestForOldVHost():
            return self.old_openid_identifier
        else:
            return self.new_openid_identifier


def account_to_openidpersistentidentity(account):
    """Adapts an `IAccount` into an `IOpenIDPersistentIdentity`."""
    return OpenIDPersistentIdentity(account)


def person_to_openidpersistentidentity(person):
    """Adapts an `IPerson` into an `IOpenIDPersistentIdentity`."""
    return OpenIDPersistentIdentity(
        removeSecurityProxy(person).account)

