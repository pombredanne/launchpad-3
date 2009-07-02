# Copyright 2009 Canonical Ltd.  All rights reserved.

"""OpenID Store related interfaces."""

__metaclass__ = type
__all__ = [
    'IProviderOpenIDStore',
    ]


from zope.interface import Interface


class IProviderOpenIDStore(Interface):
    """An association store for the SSO server's OpenID provider."""
