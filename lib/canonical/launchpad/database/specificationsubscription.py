# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['SpecificationSubscription']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.launchpad.interfaces import ISpecificationSubscription

from canonical.database.sqlbase import SQLBase


class SpecificationSubscription(SQLBase):
    """A subscription for person to a spec."""

    implements(ISpecificationSubscription)

    _table='SpecificationSubscription'
    specification = ForeignKey(dbName='specification',
        foreignKey='Specification', notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)


