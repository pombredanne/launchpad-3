# Copyright 2005 Canonical Ltd
# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = [
    'Calendar',
    'CalendarSet',
    'CalendarSubscriptionSubset',
    'CalendarEvent',
    'CalendarEventSet',
    ]

import re
import pytz

from zope.interface import implements

from sqlobject import IntervalCol, ForeignKey, IntCol, StringCol
from sqlobject import SQLMultipleJoin
from sqlobject import SQLObjectNotFound
from sqlobject import AND

from schoolbell.interfaces import ICalendarEvent
from schoolbell.mixins import CalendarMixin, EditableCalendarMixin
from schoolbell.mixins import CalendarEventMixin

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.interfaces import (
    ILaunchpadCalendar, ICalendarSet, ICalendarEventSet,
    ICalendarSubscriptionSubset, IHasOwner, IPerson, ITeam, IProject,
    IProduct, NotFoundError)


DEFAULT_COLOUR = '#efefef'
_utc_tz = pytz.timezone('UTC')

class Calendar(SQLBase, CalendarMixin, EditableCalendarMixin):
    implements(ILaunchpadCalendar)
    title = StringCol(dbName='title', notNull=True)
    revision = IntCol(dbName='revision', notNull=True, default=0)

    _parent = None
    @property
    def parent(self):
        if not self._parent:
            from canonical.launchpad.database import Person, Project, Product
            # This statement will need updating if calendars can be
            # added to other LP object types.
            # The complicated query is required because calendars can
            # have more than one type of owner.
            result = self._connection.queryAll('''
                SELECT
                  calendar.id AS calendar_id,
                  person.id   AS person_id,
                  project.id  AS project_id,
                  product.id  AS product_id
                FROM calendar
                  LEFT JOIN person  ON calendar.id = person.calendar
                  LEFT JOIN project ON calendar.id = project.calendar
                  LEFT JOIN product ON calendar.id = product.calendar
                WHERE
                  calendar.id = %s
                ''' % sqlvalues(self.id))
            # make sure we got back one row, and it corresponds to our calendar
            assert len(result) == 1
            calendar_id, person_id, project_id, product_id = result[0]
            assert calendar_id == self.id

            if person_id is not None:
                self._parent = Person.get(person_id)
            elif project_id is not None:
                self._parent = Project.get(project_id)
            elif product_id is not None:
                self._parent = Product.get(product_id)
            else:
                # should not be reached
                assert False, "Calendar is not attached to anything"
        return self._parent

    @property
    def owner(self):
        parent = self.parent
        if ITeam.providedBy(parent):
            return parent.teamowner
        elif IPerson.providedBy(parent):
            return parent
        elif IProduct.providedBy(parent) or IProject.providedBy(parent):
            return parent.owner
        else:
            # should not be reached
            assert False, "Calendar attached to unknown object"

    _eventsJoin = SQLMultipleJoin('CalendarEvent', joinColumn='calendar')

    def __iter__(self):
        """See ICalendar"""
        return iter(self._eventsJoin)

    def find(self, unique_id):
        """See ICalendar"""
        try:
            return CalendarEvent.byUniqueID(unique_id)
        except SQLObjectNotFound:
            raise NotFoundError(unique_id)

    def expand(self, first, last):
        """See ICalendar"""
        first = first.astimezone(_utc_tz)
        last = last.astimezone(_utc_tz)
        return iter(CalendarEvent.select(AND(
            CalendarEvent.q.calendarID == self.id,
            CalendarEvent.q.dtstart + CalendarEvent.q.duration > first,
            CalendarEvent.q.dtstart < last),
                                         orderBy='dtstart'))

    def addEvent(self, event):
        """See ICalendar"""
        # TODO: support recurring events
        try:
            self.find(event.unique_id)
        except NotFoundError:
            e = CalendarEvent(calendar=self, dtstart=event.dtstart,
                              duration=event.duration, title=event.title,
                              location=event.location,
                              description=event.description,
                              unique_id=event.unique_id)
            return e
        else:
            raise ValueError('event %r already in calendar' % event.unique_id)

    def removeEvent(self, event):
        """See ICalendar"""
        try:
            self.find(event.unique_id).destroySelf()
        except NotFoundError:
            raise ValueError('event %r not in calendar' % event.unique_id)


class CalendarSet:
    implements(ICalendarSet)

    def __getitem__(self, number):
        """See ICalendarSet"""
        return Calendar.get(id=number)


class CalendarSubscription(SQLBase):
    subject = ForeignKey(dbName='subject', notNull=True, foreignKey='Calendar')
    object = ForeignKey(dbName='object', notNull=True,
                          foreignKey='Calendar')
    colour = StringCol(dbName='colour', notNull=True, default=DEFAULT_COLOUR)

class CalendarSubscriptionSubset:
    """The set of subscriptions for a particular user."""
    implements(ICalendarSubscriptionSubset)

    def __init__(self, owner):
        self.owner = owner

    def __contains__(self, calendar):
        # if calendar has no ID, then it is not a database calendar
        if calendar.id is None:
            return False
        # if the person has no calendar, then they have no calendar
        # subscriptions
        if not self.owner.calendar:
            return False

        return bool(CalendarSubscription.selectBy(
            subject=self.owner.calendar, object=calendar))
    def __iter__(self):
        if self.owner.calendar:
            for sub in CalendarSubscription.select(
                    CalendarSubscription.q.subjectID==self.owner.calendar.id,
                    prejoins=['subject'],
                    clauseTables=['Calendar'],
                    orderBy=['Calendar.title']):
                yield sub.object

    def subscribe(self, calendar):
        if calendar.id is None:
            raise ValueError('calendar has no identifier')
        if calendar not in self:
            CalendarSubscription(subject=self.owner.getOrCreateCalendar(),
                                 object=calendar)
    def unsubscribe(self, calendar):
        if calendar.id is None:
            raise ValueError('calendar has no identifier')
        if not self.owner.calendar:
            # no calendar for person => no subscription
            return
        for sub in CalendarSubscription.selectBy(
                subject=self.owner.calendar, object=calendar):
            sub.destroySelf()

    def getColour(self, calendar):
        if calendar.id is None:
            return DEFAULT_COLOUR
        if not self.owner.calendar:
            return DEFAULT_COLOUR
        for sub in CalendarSubscription.selectBy(
                subject=self.owner.calendar, object=calendar):
            return sub.colour
        else:
            return DEFAULT_COLOUR

    def setColour(self, calendar, colour):
        if not re.match(r'#[0-9A-Fa-f]{6}', colour):
            raise ValueError('invalid colour value "%s"' % colour)
        if calendar.id is None:
            return
        if not self.owner.calendar:
            return
        for sub in CalendarSubscription.selectBy(
                subject=self.owner.calendar, object=calendar):
            sub.colour = colour


class CalendarEvent(SQLBase, CalendarEventMixin):
    implements(ICalendarEvent, IHasOwner)

    @property
    def owner(self):
        return self.calendar.owner

    # this field stores the unique identifier for the event, as
    # specified by the iCalendar spec.  Its value should be globally
    # unique, and preserved when exchanging calendar data with other
    # systems.
    unique_id = StringCol(dbName='uid', notNull=True, length=255,
                          alternateID=True, alternateMethodName='byUniqueID')
    calendar = ForeignKey(dbName='calendar', notNull=True,
                          foreignKey='Calendar')
    dtstart = UtcDateTimeCol(dbName='dtstart', notNull=True)

    # actually an interval ...
    duration = IntervalCol(dbName='duration', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', default='')
    location = StringCol(dbName='location', default='')

    recurrence = None # TODO: implement event recurrence


class CalendarEventSet:
    implements(ICalendarEventSet)

    def __getitem__(self, number):
        """See ICalendarEventSet"""
        number = str(number)
        if not number.isdigit():
            raise NotFoundError(
                "Unable to locate calendar event with ID %s" % number)
        try:
            return CalendarEvent.get(id=number)
        except SQLObjectNotFound:
            raise NotFoundError(
                "Unable to locate calendar event with ID %s" % number)
