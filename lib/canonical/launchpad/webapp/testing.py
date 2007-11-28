# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Testing helpers."""

__metaclass__ = type
__all__ = ['verifyObject']

from zope.interface.verify import verifyObject as zope_verifyObject
from zope.security.proxy import removeSecurityProxy


def verifyObject(iface, candidate, tentative=0):
    """A specialized verifyObject which removes the security proxy of the
    object before verifying it.
    """
    naked_candidate = removeSecurityProxy(candidate)
    return zope_verifyObject(iface, naked_candidate, tentative=0)

