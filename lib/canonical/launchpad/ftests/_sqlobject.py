# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Helper functions for testing SQLObjects."""

from zope.security.proxy import (
    removeSecurityProxy, isinstance as zope_isinstance)
from sqlobject import SQLObject


def syncUpdate(object):
    """Write the object's changes to the database."""
    if zope_isinstance(object, SQLObject):
        removeSecurityProxy(object).syncUpdate()
    else:
        raise TypeError('%r is not an SQLObject' % object)


def set_so_attr(object, colname, value):
    """Set the underlying SQLObject's column value.
    
    Use this function to setup test data when the SQLObject decendant guards
    its data. Data is guarded by transitional conditions for workflows, or
    because the decendant is conjoined to another object that controls it.
    """
    if zope_isinstance(object, SQLObject):
        attr_setter = getattr(
            removeSecurityProxy(object), '_SO_set_%s' % colname)
        attr_setter(value)
    else:
        raise TypeError('%r is not an SQLObject' % object)
