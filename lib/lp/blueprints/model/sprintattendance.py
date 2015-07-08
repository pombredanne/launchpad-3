# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = ['SprintAttendance']

from storm.locals import (
    Bool,
    Int,
    Reference,
    )
from zope.interface import implementer

from lp.blueprints.interfaces.sprintattendance import ISprintAttendance
from lp.registry.interfaces.person import validate_public_person
from lp.services.database.datetimecol import UtcDateTimeCol
from lp.services.database.stormbase import StormBase


@implementer(ISprintAttendance)
class SprintAttendance(StormBase):
    """A record of the attendance of a person at a sprint."""

    __storm_table__ = 'SprintAttendance'

    id = Int(primary=True)

    sprint_id = Int(name='sprint')
    sprint = Reference(sprint_id, 'Sprint.id')

    attendeeID = Int(name='attendee', validator=validate_public_person)
    attendee = Reference(attendeeID, 'Person.id')

    time_starts = UtcDateTimeCol(notNull=True)
    time_ends = UtcDateTimeCol(notNull=True)
    _is_physical = Bool(name='is_physical', default=True)

    def __init__(self, sprint, attendee):
        self.sprint = sprint
        self.attendee = attendee

    @property
    def is_physical(self):
        return self.sprint.is_physical and self._is_physical
