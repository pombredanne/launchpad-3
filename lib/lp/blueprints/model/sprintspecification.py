# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = ['SprintSpecification']

from sqlobject import (
    ForeignKey,
    StringCol,
    )
from zope.interface import implements

from canonical.database.constants import (
    DEFAULT,
    UTC_NOW,
    )
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from lp.blueprints.enums import SprintSpecificationStatus
from lp.blueprints.interfaces.sprintspecification import ISprintSpecification
from lp.registry.interfaces.person import validate_public_person


class SprintSpecification(SQLBase):
    """A link between a sprint and a specification."""

    implements(ISprintSpecification)

    _table = 'SprintSpecification'

    sprint = ForeignKey(dbName='sprint', foreignKey='Sprint',
        notNull=True)
    specification = ForeignKey(dbName='specification',
        foreignKey='Specification', notNull=True)
    status = EnumCol(schema=SprintSpecificationStatus, notNull=True,
        default=SprintSpecificationStatus.PROPOSED)
    whiteboard = StringCol(notNull=False, default=None)
    registrant = ForeignKey(
        dbName='registrant', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    decider = ForeignKey(
        dbName='decider', foreignKey='Person',
        storm_validator=validate_public_person, notNull=False, default=None)
    date_decided = UtcDateTimeCol(notNull=False, default=None)

    @property
    def is_confirmed(self):
        """See ISprintSpecification."""
        return self.status == SprintSpecificationStatus.ACCEPTED

    @property
    def is_decided(self):
        """See ISprintSpecification."""
        return self.status != SprintSpecificationStatus.PROPOSED

    def acceptBy(self, decider):
        """See ISprintSpecification."""
        self.status = SprintSpecificationStatus.ACCEPTED
        self.decider = decider
        self.date_decided = UTC_NOW

    def declineBy(self, decider):
        """See ISprintSpecification."""
        self.status = SprintSpecificationStatus.DECLINED
        self.decider = decider
        self.date_decided = UTC_NOW

