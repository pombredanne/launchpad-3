from zope.interface import implements

from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, EnumCol
from sqlobject import MultipleJoin
from sqlobject import SQLObjectNotFound
from sqlobject import AND

from schoolbell.interfaces import ICalendarEvent
from schoolbell.mixins import CalendarMixin, EditableCalendarMixin
from schoolbell.mixins import CalendarEventMixin

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import ILaunchpadCalendar, IHasOwner

import datetime
import pytz

_utc_tz = pytz.timezone('UTC')

class Calendar(SQLBase, CalendarMixin, EditableCalendarMixin):
    implements(ILaunchpadCalendar)
    owner = ForeignKey(dbName='owner', notNull=True, foreignKey='Person')
    title = StringCol(dbName='title', notNull=True)
    revision = IntCol(dbName='revision', notNull=True, default=0)

    _eventsJoin = MultipleJoin('CalendarEvent', joinColumn='calendar')

    def __iter__(self):
        return iter(self._eventsJoin)

    def find(self, unique_id):
        try:
            return CalendarEvent.byUniqueID(unique_id)
        except SQLObjectNotFound:
            raise KeyError(unique_id)

    def expand(self, first, last):
        first = first.astimezone(_utc_tz)
        last = last.astimezone(_utc_tz)
        return iter(CalendarEvent.select(AND(
            CalendarEvent.q.calendarID == self.id,
            CalendarEvent.q.dtstart + CalendarEvent.q.duration > first,
            CalendarEvent.q.dtstart < last),
                                         orderBy='dtstart'))

    def addEvent(self, event):
        # TODO: support recurring events
        try:
            # XXX: the database has unique columns, so find should not be
            # necessary -- only my ConnectionStub doesn't know about unique
            # indexes yet.
            self.find(event.unique_id)
        except:
            e = CalendarEvent(calendar=self, dtstart=event.dtstart,
                              duration=event.duration, title=event.title,
                              location=event.location, description=event.description,
                              unique_id=event.unique_id)
            return e
        else:
            raise ValueError('event %r already in calendar' % event.unique_id)

    def removeEvent(self, event):
        try:
            self.find(event.unique_id).destroySelf()
        except KeyError:
            raise ValueError('event %r not in calendar' % event.unique_id)

    # TODO: implement clear() more directly


class CalendarSubscription(SQLBase):
    person = ForeignKey(dbName='person', notNull=True, foreignKey='Person')
    calendar = ForeignKey(dbName='calendar', notNull=True,
                          foreignKey='Calendar')
    colour = StringCol(dbName='colour', notNull=True, default='#9db8d2')

class CalendarEvent(SQLBase, CalendarEventMixin):
    implements(ICalendarEvent, IHasOwner)

    def owner(self):
        return self.calendar.owner
    owner = property(owner)

    unique_id = StringCol(dbName='unique_id', notNull=True, length=255,
                          alternateID=True, alternateMethodName='byUniqueID')
    calendar = ForeignKey(dbName='calendar', notNull=True,
                          foreignKey='Calendar')
    dtstart = DateTimeCol(dbName='dtstart', notNull=True)
    def _get_dtstart(self):
        '''Add a UTC timezone to the timestamp'''
        value = self._SO_get_dtstart()
        if value:
            return datetime.datetime(value.year, value.month, value.day,
                                     value.hour, value.minute, value.second,
                                     tzinfo=_utc_tz)
        else:
            return None
    def _set_dtstart(self, value):
        '''Convert timestamp to UTC'''
        if value:
            value = value.astimezone(_utc_tz)
        self._SO_set_dtstart(value)
        
    # actually an interval ...
    duration = DateTimeCol(dbName='duration', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=True, default='')
    location = StringCol(dbName='location', notNull=True, default='')

    recurrence = None # TODO: implement this as a property

    # The following attributes are all used for recurring events
    recurrence_type = EnumCol(dbName='recurrence', notNull=True,
                              enumValues=['', 'SECONDLY', 'MINUTELY', 'HOURLY',
                                          'DAILY', 'WEEKLY', 'MONTHLY',
                                          'YEARLY'],
                              default='')
    count = IntCol(dbName='count', default=None)
    until = DateTimeCol(dbName='until', default=None)
    def _get_until(self):
        '''Add a UTC timezone to the timestamp'''
        value = self._SO_get_until()
        if value:
            return datetime.datetime(value.year, value.month, value.day,
                                     value.hour, value.minute, value.second,
                                     tzinfo=_utc_tz)
        else:
            return None
    def _set_until(self, value):
        '''Convert timestamp to UTC'''
        if value:
            value = value.astimezone(_utc_tz)
        self._SO_set_until(value)

    exceptions = StringCol(dbName='exceptions', default=None)
    interval = IntCol(dbName='interval', default=None)
    rec_list = StringCol(dbName='rec_list', default=None)

