# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from zope.interface.common.interfaces import IRuntimeError
from zope.schema import Int
from sqlos.interfaces import ISQLObject

class IRequestExpired(IRuntimeError):
    """A RequestExpired exception is raised if the current request has
    timed out.
    """

class ISQLBase(ISQLObject):
    """An extension of ISQLObject that provides an ID."""
    id = Int(title=u"The integer ID for the instance")

