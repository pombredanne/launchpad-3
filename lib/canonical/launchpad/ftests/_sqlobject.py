# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helper functions for testing SQLObjects."""

__all__ = [
    'print_date_attribute',
    'sync',
    ]

from storm.sqlobject import SQLObjectBase as SQLObject
from zope.security.proxy import (
    isinstance as zope_isinstance,
    removeSecurityProxy,
    )

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import sqlvalues


def sync(object):
    """Sync the object's from the database.

    This is useful if the object's connection was commited in Zopeless mode,
    or if the database was updated outside the ORM.
    """
    if zope_isinstance(object, SQLObject):
        removeSecurityProxy(object).sync()
    else:
        raise TypeError('%r is not an SQLObject' % object)


def print_date_attribute(object, colname):
    """Print out a date attribute of an SQLObject, possibly as 'UTC_NOW'.

    If the value of the attribute is equal to the 'UTC_NOW' time of the
    current transaction, it prints the string 'UTC_NOW' instead of the actual
    time value.  This helps write more precise doctests.
    """
    if zope_isinstance(object, SQLObject):
        cls = removeSecurityProxy(object).__class__
        query_template = 'id=%%s AND %s=%%s' % colname
        found_object = cls.selectOne(
            query_template % sqlvalues(object.id, UTC_NOW))
        if found_object is None:
            print getattr(object, colname)
        else:
            print 'UTC_NOW'
    else:
        raise TypeError('%r is not an SQLObject' % object)
