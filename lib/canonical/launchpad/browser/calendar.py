
import re
import datetime

from zope.interface import implements
from canonical.launchpad.interfaces import ICalendarView, ICalendarWeekView
#from canonical.launchpad.interfaces import ICalendarDayView, ICalendarMonthView
#from canonical.launchpad.interfaces import ICalendarYearView

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
                       week=int(match.group(2)),
                       day=int(match.group(3)))

class CalendarView(object):
    """Base class for the various calendar views"""
    implements(ICalendarView)

    def __init__(self, calendar, datestring):
        self.calendar = calendar
        self.datestring = datestring

class WeekView(CalendarView):
    """A week view of the calendar."""
    implements(ICalendarWeekView)

    def __init__(self, calendar, year, week):
        CalendarView.__init__(self, calendar, '%04d-W%02d' % (year, week))
        self.year = year
        self.week = week
