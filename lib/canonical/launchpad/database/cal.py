from zope.interface import implements

from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, EnumCol
from sqlobject import MultipleJoin
from sqlobject import SQLObjectNotFound

from schoolbell.interfaces import ICalendarEvent
from schoolbell.mixins import CalendarMixin, CalendarEventMixin

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import ILaunchpadCalendar

import datetime

class Calendar(SQLBase, CalendarMixin):
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


class CalendarSubscription(SQLBase):
    person = ForeignKey(dbName='person', notNull=True, foreignKey='Person')
    calendar = ForeignKey(dbName='calendar', notNull=True,
                          foreignKey='Calendar')


class CalendarEvent(SQLBase, CalendarEventMixin):
    implements(ICalendarEvent)

    unique_id = StringCol(dbName='unique_id', notNull=True, length=255,
                          alternateID=True, alternateMethodName='byUniqueID')
    calendar = ForeignKey(dbName='calendar', notNull=True,
                          foreignKey='Calendar')
    dtstart = DateTimeCol(dbName='dtstart', notNull=True)
    # actually an interval ...
    duration = DateTimeCol(dbName='duration', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    location = StringCol(dbName='location', notNull=True, default='')

    # The following attributes are all used for recurring events
    recurrence = EnumCol(dbName='recurrence', notNull=True,
                         enumValues=['', 'SECONDLY', 'MINUTELY', 'HOURLY',
                                     'DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY'],
                         default='')
    count = IntCol(dbName='count', default=None)
    until = DateTimeCol(dbName='until', default=None)
    exceptions = StringCol(dbName='exceptions', default=None)
    interval = IntCol(dbName='interval', default=None)
    rec_list = StringCol(dbName='rec_list', default=None)

    def not_implemented(*args, **kw):
        raise NotImplementedError

    hasOccurrences = not_implemented    # TODO
    replace = not_implemented           # TODO

