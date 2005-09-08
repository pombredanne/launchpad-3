# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['SpecificationBug']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.launchpad.interfaces import ISpecificationBug

from canonical.database.sqlbase import SQLBase


class SpecificationBug(SQLBase):
    """A link between a spec and a bug."""

    implements(ISpecificationBug)

    _table='SpecificationBug'
    specification = ForeignKey(dbName='specification',
        foreignKey='Specification', notNull=True)
    bug = ForeignKey(dbName='bug', foreignKey='Bug',
        notNull=True)


