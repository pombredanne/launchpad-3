# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = ['SprintAttendance']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.launchpad.interfaces import ISprintAttendance
from canonical.launchpad.validators.person import validate_public_person

from canonical.database.datetimecol import UtcDateTimeCol

from canonical.database.sqlbase import SQLBase


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


