
import re
import calendar
from datetime import datetime, date, timedelta, tzinfo

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from zope.interface import implements
from canonical.launchpad.interfaces import ICalendarView, ICalendarWeekView
from canonical.launchpad.interfaces import ICalendarDayView, ICalendarMonthView
from canonical.launchpad.interfaces import ICalendarYearView
from canonical.launchpad.interfaces import ICalendarDayInfo, ICalendarEventInfo

from schoolbell.utils import prev_month, next_month
from schoolbell.utils import weeknum_bounds, check_weeknum

daynames = [
    _("Monday"),
    _("Tuesday"),
    _("Wednesday"),
    _("Thursday"),
    _("Friday"),
    _("Saturday"),
    _("Sunday")
    ]
monthnames = [
    _("January"),
    _("February"),
    _("March"),
    _("April"),
    _("May"),
    _("June"),
    _("July"),
    _("August"),
    _("September"),
    _("October"),
    _("November"),
    _("December")
    ]

# XXX this should really be the user's timezone
class UtcTimeZone(tzinfo):
    def utcoffset(self, dt):
        return timedelta(0)
    def tzname(self, dt):
        return "UTC"
    def dst(self, dt):
        return timedelta(0)
class PerthTimeZone(tzinfo):
    def utcoffset(self, dt):
        return timedelta(hours=8)
    def tzname(self, dt):
        return "AWST"
    def dst(self, dt):
        return timedelta(0)
UTC = UtcTimeZone()
user_timezone = PerthTimeZone()

# XXXX we don't actually have any of these view classes yet ...
_year_pat  = re.compile(r'^(\d\d\d\d)$')
_month_pat = re.compile(r'^(\d\d\d\d)-(\d\d)$')
_week_pat  = re.compile(r'^(\d\d\d\d)-W(\d\d)$')
_day_pat   = re.compile(r'^(\d\d\d\d)-(\d\d)-(\d\d)$')
def traverseCalendar(calendar, request, name):
    match = _year_pat.match(name)
    if match:
        return YearView(calendar,
                        year=int(match.group(1)))
    match = _month_pat.match(name)
    if match:
        return MonthView(calendar,
                         year=int(match.group(1)),
                         month=int(match.group(2)))
    match = _week_pat.match(name)
    if match:
        return WeekView(calendar,
                        year=int(match.group(1)),
                        week=int(match.group(2)))
    match = _day_pat.match(name)
    if match:
        return DayView(calendar,
                       year=int(match.group(1)),
                       month=int(match.group(2)),
                       day=int(match.group(3)))
    now = datetime.now(user_timezone)
    if name == 'today':
        return DayView(calendar,
                       year=now.year,
                       month=now.month,
                       day=now.day)
    elif name == 'this-week':
        isoyear, isoweek, isoday = now.isocalendar()
        return WeekView(calendar,
                        year=isoyear,
                        week=isoweek)
    elif name == 'this-month':
        return MonthView(calendar,
                         year=now.year,
                         month=now.month)
    elif name == 'this-year':
        return MonthView(calendar,
                         year=now.year)

class CalendarView(object):
    """Base class for the various calendar views"""
    implements(ICalendarView)

    def __init__(self, calendar, datestring):
        self.calendar = calendar
        self.datestring = datestring

    def _setViewURLs(self, date):
        """Computes the URLs used to switch calendar views."""
        self.dayViewURL = '../%04d-%02d-%02d' % (date.year,
                                                 date.month,
                                                 date.day)
        (isoyear, isoweek, isoday) = date.isocalendar()
        self.weekViewURL = '../%04d-W%02d' % (isoyear, isoweek)
        self.monthViewURL = '../%04d-%02d' % (date.year, date.month)
        self.yearViewURL = '../%04d' % date.year

class DayInfo(object):
    implements(ICalendarDayInfo)

    def __init__(self, date):
        self.date = date
        self.dayname = daynames[self.date.weekday()]
        self.dayURL = '../%04d-%02d-%02d' % (date.year,
                                             date.month,
                                             date.day)
        self.events = []
    def hasEvents(self):
        return len(self.events) != 0
    hasEvents = property(hasEvents)

class EventInfo(object):
    implements(ICalendarEventInfo)
    def __init__(self, event):
        self.event = event
        self.dtstart = event.dtstart.astimezone(user_timezone)
        self.timestring = '%02d:%02d' % (self.dtstart.hour,
                                         self.dtstart.minute)

class DayView(CalendarView):
    """A day view of the calendar."""
    implements(ICalendarDayView)

    def __init__(self, calendar, year, month, day):
        self.day = date(year, month, day)
        datestring = '%d %s %04d' % (day, monthnames[month-1], year)
        CalendarView.__init__(self, calendar, datestring)

        # navigation links
        yesterday = self.day - timedelta(days=1)
        self.prevURL = '../%04d-%02d-%02d' % (yesterday.year,
                                              yesterday.month,
                                              yesterday.day)
        tomorrow = self.day + timedelta(days=1)
        self.nextURL = '../%04d-%02d-%02d' % (tomorrow.year,
                                              tomorrow.month,
                                              tomorrow.day)
        self._setViewURLs(self.day)

class WeekView(CalendarView):
    """A week view of the calendar."""
    implements(ICalendarWeekView)

    def __init__(self, cal, year, week):
        assert check_weeknum(year, week), 'invalid week number'
        CalendarView.__init__(self, cal, 'Week %d, %04d' % (week, year))
        self.year = year
        self.week = week
        (start, end) = weeknum_bounds(year, week)

        # navigation links
        (isoyear, isoweek, isoday) = (start - timedelta(days=1)).isocalendar()
        self.prevURL = '../%04d-W%02d' % (isoyear, isoweek)
        (isoyear, isoweek, isoday) = (end + timedelta(days=1)).isocalendar()
        self.nextURL = '../%04d-W%02d' % (isoyear, isoweek)

        self._setViewURLs(start)

        self.days = []
        for i in range(7):
            day = DayInfo(start + timedelta(days=i))
            self.days.append(day)
        # XXXX : would be nice if I didn't need these.
        self.monday = self.days[0]
        self.tuesday = self.days[1]
        self.wednesday = self.days[2]
        self.thursday = self.days[3]
        self.friday = self.days[4]
        self.saturday = self.days[5]
        self.sunday = self.days[6]

        # find events for the week
        self.events = []
        start = datetime(start.year, start.month, start.day,
                         0, 0, 0, 0, user_timezone).astimezone(UTC)
        end = start + timedelta(weeks=1)
        for event in self.calendar.expand(start, end):
            ev = EventInfo(event)
            self.days[ev.dtstart.weekday()].events.append(ev)

class MonthView(CalendarView):
    """A month view of the calendar."""
    implements(ICalendarMonthView)

    daynames = daynames

    def __init__(self, cal, year, month):
        assert 1 <= month <= 12, 'invalid month number'
        datestring = '%s %04d' % (monthnames[month-1], year)
        CalendarView.__init__(self, cal, datestring)
        self.year = year
        self.month = month
        start = date(year, month, 1)

        # navigation links
        prev = prev_month(start)
        self.prevURL = '../%04d-%02d' % (prev.year, prev.month)
        next = next_month(start)
        self.nextURL = '../%04d-%02d' % (next.year, next.month)

        self._setViewURLs(start)

        # create dayinfo instances for each day of the month
        days = []
        for i in range(calendar.monthrange(year, month)[1]):
            days.append(DayInfo(date(year, month, i+1)))

        # convert to UTC time offsets
        start = datetime(start.year, start.month, start.day,
                         0, 0, 0, 0, user_timezone).astimezone(UTC)
        end = datetime(next.year, next.month, next.day,
                         0, 0, 0, 0, user_timezone).astimezone(UTC)

        for event in self.calendar.expand(start, end):
            ev = EventInfo(event)
            self.days[ev.dtstart.day - 1].events.append(ev)

        # lay out the dayinfo objects in a 2D grid
        layout = calendar.monthcalendar(year, month)
        self.days = []
        for layout_row in layout:
            row = []
            for item in layout_row:
                if item == 0:
                    row.append(None)
                else:
                    row.append(days[item - 1])
            self.days.append(row)

class YearView(CalendarView):
    """A month view of the calendar."""
    implements(ICalendarYearView)

    def __init__(self, cal, year):
        CalendarView.__init__(self, cal, '%04d' % year)
        self.year = year
        start = date(year, 1, 1)
        end = date(year+1, 1, 1) - timedelta(days=1)
        self.bounds = [start, end]

        # navigation links
        self.prevURL = '../%04d' % (year - 1)
        self.nextURL = '../%04d' % (year + 1)

        self._setViewURLs(start)

