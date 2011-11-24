# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for the Launchpad security policy."""

__metaclass__ = type

__all__ = [
    'IAuthorization',
    ]

from zope.interface import Interface


class IAuthorization(Interface):
    """Authorization policy for a particular object and permission."""

    def checkUnauthenticated():
        """Returns True if an unauthenticated user has that permission
        on the adapted object.  Otherwise returns False.
        """

    def checkAccountAuthenticated(account):
        """Returns True if the account has that permission on the adapted
        object.  Otherwise returns False.

        The argument `account` is the account who is authenticated.
        """
