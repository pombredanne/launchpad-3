# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""OpenID Store related interfaces."""

__metaclass__ = type
__all__ = [
    'IProviderOpenIDStore',
    ]


from zope.interface import Interface


class IProviderOpenIDStore(Interface):
    """An association store for the SSO server's OpenID provider."""
