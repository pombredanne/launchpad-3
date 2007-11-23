# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

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

    @property
    def target(self):
        """See IBugLink."""
        return self.specification

