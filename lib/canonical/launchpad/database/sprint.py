# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'Sprint',
    'SprintSet',
    ]

import datetime

from zope.interface import implements

from sqlobject import (
    ForeignKey, IntCol, StringCol, MultipleJoin, RelatedJoin)

from canonical.launchpad.interfaces import ISprint, ISprintSet, NotFoundError

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.validators.name import valid_name

from canonical.launchpad.database.sprintattendance import SprintAttendance
from canonical.launchpad.database.sprintspecification import (
    SprintSpecification)


class Sprint(SQLBase):
    """See ISprint."""

    implements(ISprint)

    _defaultOrder = ['name']

    # db field names
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    name = StringCol(notNull=True)
    title = StringCol(notNull=True)
    summary = StringCol(notNull=True)
    home_page = StringCol(notNull=False, default=None)
    address = StringCol(notNull=False, default=None)
    datecreated = UtcDateTimeCol(notNull=True, default=DEFAULT)
    time_zone = StringCol(notNull=True)
    time_starts = UtcDateTimeCol(notNull=True)
    time_ends = UtcDateTimeCol(notNull=True)

    # useful joins
    attendees = RelatedJoin('Person',
        joinColumn='sprint', otherColumn='attendee',
        intermediateTable='SprintAttendance', orderBy='name')
    specifications = RelatedJoin('Specification',
        joinColumn='sprint', otherColumn='specification',
        intermediateTable='SprintSpecification',
        orderBy=['name', 'title', 'id'])

    @property
    def attendances(self):
        ret = SprintAttendance.selectBy(sprintID=self.id)
        return sorted(ret, key=lambda a: a.attendee.name)

    def specificationLinks(self, status=None):
        """See ISprint."""
        query = 'sprint=%s' % sqlvalues(self.id)
        if status is not None:
            query += ' AND status=%s' % sqlvalues(status)
        sprintspecs = SprintSpecification.select(query)
        return sorted(sprintspecs, key=lambda a: a.specification.priority,
            reverse=True)

    # attendance
    def attend(self, person, time_starts, time_ends):
        """See ISprint."""
        # first see if a relevant attendance exists, and if so, update it
        for attendance in self.attendances:
            if attendance.attendee.id == person.id:
                attendance.time_starts = time_starts
                attendance.time_ends = time_ends
                return attendance
        # since no previous attendance existed, create a new one
        return SprintAttendance(sprint=self, attendee=person,
            time_starts=time_starts, time_ends=time_ends)

    def removeAttendance(self, person):
        """See ISprint."""
        for attendance in self.attendances:
            if attendance.attendee.id == person.id:
                attendance.destroySelf()
                return

    # linking to specifications
    def linkSpecification(self, spec):
        """See ISprint."""
        for speclink in self.spec_links:
            if speclink.spec.id == spec.id:
                return speclink
        return SprintSpecification(sprint=self, specification=spec)

    def unlinkSpecification(self, spec):
        """See ISprint."""
        for speclink in self.spec_links:
            if speclink.spec.id == spec.id:
                SprintSpecification.delete(speclink.id)
                return speclink


class SprintSet:
    """The set of sprints."""

    implements(ISprintSet)

    def __init__(self):
        """See ISprintSet."""
        self.title = 'Sprints and Meetings'

    def __getitem__(self, name):
        """See ISprintSet."""
        return Sprint.selectOneBy(name=name)

    def __iter__(self):
        """See ISprintSet."""
        return iter(Sprint.select(orderBy='-time_starts'))

    def new(self, owner, name, title, time_zone, time_starts, time_ends,
        summary=None, home_page=None):
        """See ISprintSet."""
        return Sprint(owner=owner, name=name, title=title,
            time_zone=time_zone, time_starts=time_starts,
            time_ends=time_ends, summary=summary, home_page=home_page)

