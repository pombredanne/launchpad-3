from zope.interface import implements

from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, EnumCol

from canonical.database.sqlbase import SQLBase
from schoolbell.interfaces import ICalendar
from canonical.launchpad.interfaces import ILaunchpadCalendar

import datetime

class Calendar(SQLBase):
    implements(ICalendar, ILaunchpadCalendar)
    owner = ForeignKey(dbName='owner', notNull=True, foreignKey='Person')
    title = StringCol(dbName='title', notNull=True)
    revision = IntCol(dbName='revision', notNull=True)

class CalendarSubscription(SQLBase):
    person = ForeignKey(dbName='person', notNull=True, foreignKey='Person')
    calendar = ForeignKey(dbName='calendar', notNull=True, foreignKey='Calendar')

class CalendarEvent(SQLBase):
    unique_id = StringCol(dbName='unique_id', notNull=True, length=255)
    calendar = ForeignKey(dbName='calendar', notNull=True, foreignKey='Calendar')
    dtstart = DateTimeCol(dbName='dtstart', notNull=True)
    # actually an interval ...
    duration = DateTimeCol(dbName='duration', notNull=True)
    location = StringCol(dbName='location', notNull=True)
    recurrence = EnumCol(dbName='recurrence', notNull=True,
                         enumValues=['', 'SECONDLY', 'MINUTELY', 'HOURLY',
                                     'DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY'])
    count = IntCol(dbName='count')
    until = DateTimeCol(dbName='until')
    exceptions = StringCol(dbName='exceptions')
    interval = IntCol(dbName='interval')
    rec_list = StringCol(dbName='rec_list')
