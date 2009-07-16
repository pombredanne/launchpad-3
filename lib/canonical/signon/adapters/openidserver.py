# Copyright 2008 Canonical Ltd.  All rights reserved.

"""OpenID adapters and helper objects."""

__metaclass__ = type

__all__ = [
    'CurrentOpenIDEndPoint',
    ]

from canonical.launchpad.webapp.vhosts import allvhosts


class CurrentOpenIDEndPoint:
    """A utility for working with multiple OpenID End Points."""

    @classmethod
    def getServiceURL(cls):
        """The OpenID server URL (/+openid) for the current request."""
        return allvhosts.configs['openid'].rooturl + '+openid'

    @classmethod
    def supportsURL(cls, identity_url):
        """Does the OpenID current vhost support the identity_url?"""
        root_url = allvhosts.configs['openid'].rooturl
        return identity_url.startswith(root_url + '+id')
