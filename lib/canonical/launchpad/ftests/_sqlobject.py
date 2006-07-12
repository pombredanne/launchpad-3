# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Helper functions for testing SQLObjects."""

from zope.security.proxy import (
    removeSecurityProxy, isinstance as zope_isinstance)
from sqlobject import SQLObject
from zope.app.pagetemplate.engine import Engine

def syncUpdate(object):
    if zope_isinstance(object, SQLObject):
        removeSecurityProxy(object).syncUpdate()
    else:
        raise TypeError('%r is not an SQLObject' % object)
