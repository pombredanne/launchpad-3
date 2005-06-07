import datetime
import pytz

from zope.interface import implements

from sqlobject import IntervalCol, ForeignKey, IntCol, StringCol, EnumCol
from sqlobject import MultipleJoin
from sqlobject import SQLObjectNotFound
from sqlobject import AND

from schoolbell.interfaces import ICalendarEvent
from schoolbell.mixins import CalendarMixin, EditableCalendarMixin
from schoolbell.mixins import CalendarEventMixin

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.interfaces import ILaunchpadCalendar, IHasOwner

_utc_tz = pytz.timezone('UTC')

class Calendar(SQLBase, CalendarMixin, EditableCalendarMixin):
    implements(ILaunchpadCalendar)
    title = StringCol(dbName='title', notNull=True)
    revision = IntCol(dbName='revision', notNull=True, default=0)

    _parent = None
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
                FROM ((calendar
                  LEFT JOIN person  ON calendar.id = person.calendar)
                  LEFT JOIN project ON calendar.id = project.calendar)
                  LEFT JOIN product ON calendar.id = product.calendar
                WHERE
                  calendar.id = %s
                ''' % sqlvalues(self.id))
            # make sure we got back one row, and it corresponds to our calendar
            assert len(result) == 1
            result = result[0]
            assert result[0] == self.id

            if result[1] is not None: # person
                self._parent = Person.get(result[1])
            elif result[2] is not None:
                self._parent = Project.get(result[2])
            elif result[3] is not None:
                self._parent = Product.get(result[3])
            else:
                # should not be reached
                assert False, "Calendar is not attached to anything"
        return self._parent
    parent = property(parent)

    def owner(self):
        from canonical.launchpad.database import Person, Project, Product
        parent = self.parent
        if isinstance(parent, Person):
            if parent.isTeam():
                return parent.teamowner
            else:
                return parent
        elif isinstance(parent, (Project, Product)):
            return parent.owner
        else:
            # should not be reached
            assert False, "Calendar attached to unknown object"
    owner = property(owner)

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
    subject = ForeignKey(dbName='subject', notNull=True, foreignKey='Calendar')
    object = ForeignKey(dbName='object', notNull=True,
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
    dtstart = UtcDateTimeCol(dbName='dtstart', notNull=True)
        
    # actually an interval ...
    duration = IntervalCol(dbName='duration', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=True, default='')
    location = StringCol(dbName='location', default='')

    recurrence = None # TODO: implement this as a property

##     # The following attributes are all used for recurring events
##     recurrence_type = EnumCol(dbName='recurrence', notNull=True,
##                               enumValues=['', 'SECONDLY', 'MINUTELY', 'HOURLY',
##                                           'DAILY', 'WEEKLY', 'MONTHLY',
##                                           'YEARLY'],
##                               default='')
##     count = IntCol(dbName='count', default=None)
##     until = UtcDateTimeCol(dbName='until', default=None)

##     exceptions = StringCol(dbName='exceptions', default=None)
##     interval = IntCol(dbName='interval', default=None)
##     rec_list = StringCol(dbName='rec_list', default=None)

