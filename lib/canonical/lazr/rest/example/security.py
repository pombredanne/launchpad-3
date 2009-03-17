# Copyright 2009 Canonical Ltd.  All rights reserved.

"""A simple security policy for the LAZR example web service."""

__metaclass__ = type
__all__ = [
    'CookbookWebServiceSecurityPolicy',
]

from zope.security.simplepolicies import PermissiveSecurityPolicy
from zope.security.proxy import removeSecurityProxy
from canonical.lazr.rest.example.interfaces import IRecipe


class CookbookWebServiceSecurityPolicy(PermissiveSecurityPolicy):
    """A very basic security policy."""

    def checkPermission(self, permission, object):
        """Private recipes are hidden; all other objects are visible."""
        if IRecipe.providedBy(object):
            return not removeSecurityProxy(object).private
        else:
            return True

