# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'SpecificationWorkItem',
    ]

from zope.interface import implements

from sqlobject import (
    BoolCol,
    ForeignKey,
    StringCol,
    )

from lp.services.database.constants import DEFAULT
from lp.services.database.datetimecol import UtcDateTimeCol
from lp.services.database.enumcol import EnumCol
from lp.services.database.sqlbase import SQLBase

from lp.blueprints.enums import SpecificationWorkItemStatus
from lp.blueprints.interfaces.specificationworkitem import (
    ISpecificationWorkItem,
    )
from lp.registry.interfaces.person import validate_public_person


class SpecificationWorkItem(SQLBase):
    implements(ISpecificationWorkItem)

    title = StringCol(notNull=True)
    specification = ForeignKey(foreignKey='Specification', notNull=True)
    assignee = ForeignKey(
        notNull=False, foreignKey='Person',
        storm_validator=validate_public_person, default=None)
    milestone = ForeignKey(
        foreignKey='Milestone', notNull=False, default=None)
    status = EnumCol(
        schema=SpecificationWorkItemStatus,
        notNull=True, default=SpecificationWorkItemStatus.TODO)
    datecreated = UtcDateTimeCol(notNull=True, default=DEFAULT)
    deleted = BoolCol(notNull=True, default=False)

    def __repr__(self):
        return '<SpecificationWorkItem [%s] %s: %s of %s>' % (
            self.assignee, self.title, self.status, self.specification)

