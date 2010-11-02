# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = ['SprintAttendance']

from sqlobject import (
    BoolCol,
    ForeignKey,
    )
from zope.interface import implements

from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from lp.blueprints.interfaces.sprintattendance import ISprintAttendance
from lp.registry.interfaces.person import validate_public_person


class SprintAttendance(SQLBase):
    """A record of the attendance of a person at a sprint."""

    implements(ISprintAttendance)

    _table = 'SprintAttendance'

    sprint = ForeignKey(dbName='sprint', foreignKey='Sprint',
        notNull=True)
    attendee = ForeignKey(
        dbName='attendee', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    time_starts = UtcDateTimeCol(notNull=True)
    time_ends = UtcDateTimeCol(notNull=True)
    is_physical = BoolCol(dbName='is_physical', notNull=True, default=True)
