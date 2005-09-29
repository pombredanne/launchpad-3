# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['SprintSpecification']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.launchpad.interfaces import ISprintSpecification

from canonical.database.sqlbase import SQLBase


class SprintSpecification(SQLBase):
    """A link between a sprint and a specification."""

    implements(ISprintSpecification)

    _table='SprintSpecification'

    sprint = ForeignKey(dbName='sprint', foreignKey='Sprint',
        notNull=True)
    specification = ForeignKey(dbName='specification',
        foreignKey='Specification', notNull=True)


