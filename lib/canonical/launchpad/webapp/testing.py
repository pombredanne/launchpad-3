# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

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

