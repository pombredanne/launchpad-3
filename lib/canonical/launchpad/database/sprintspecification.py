# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['SprintSpecification']

from zope.interface import implements

from sqlobject import ForeignKey, BoolCol, StringCol

from canonical.launchpad.interfaces import ISprintSpecification

from canonical.lp.dbschema import EnumCol, SprintSpecificationStatus

from canonical.database.sqlbase import SQLBase


class SprintSpecification(SQLBase):
    """A link between a sprint and a specification."""

    implements(ISprintSpecification)

    _table='SprintSpecification'

    sprint = ForeignKey(dbName='sprint', foreignKey='Sprint',
        notNull=True)
    specification = ForeignKey(dbName='specification',
        foreignKey='Specification', notNull=True)
    status = EnumCol(schema=SprintSpecificationStatus, notNull=True,
        default=SprintSpecificationStatus.SUBMITTED)
    needs_discussion = BoolCol(notNull=True, default=True)
    whiteboard = StringCol(notNull=False, default=None)

