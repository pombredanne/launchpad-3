
import re
import calendar
from datetime import datetime, date, timedelta

from zope.interface import implements
from canonical.launchpad.interfaces import ICalendarView, ICalendarWeekView
from canonical.launchpad.interfaces import ICalendarDayView, ICalendarMonthView
from canonical.launchpad.interfaces import ICalendarYearView

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

def prev_month(date):
    """Calculate the first day of the previous month for a given date.

        >>> prev_month(date(2004, 8, 1))
        datetime.date(2004, 7, 1)
        >>> prev_month(date(2004, 8, 31))
        datetime.date(2004, 7, 1)
        >>> prev_month(date(2004, 12, 15))
        datetime.date(2004, 11, 1)
        >>> prev_month(date(2005, 1, 28))
        datetime.date(2004, 12, 1)

    """
    return (date.replace(day=1) - timedelta(1)).replace(day=1)


def next_month(date):
    """Calculate the first day of the next month for a given date.

        >>> next_month(date(2004, 8, 1))
        datetime.date(2004, 9, 1)
        >>> next_month(date(2004, 8, 31))
        datetime.date(2004, 9, 1)
        >>> next_month(date(2004, 12, 15))
        datetime.date(2005, 1, 1)
        >>> next_month(date(2004, 2, 28))
        datetime.date(2004, 3, 1)
        >>> next_month(date(2004, 2, 29))
        datetime.date(2004, 3, 1)
        >>> next_month(date(2005, 2, 28))
        datetime.date(2005, 3, 1)

    """
    return (date.replace(day=28) + timedelta(7)).replace(day=1)


def week_start(date, first_day_of_week=0):
    """Calculate the first day of the week for a given date.

    Assuming that week starts on Mondays:

        >>> week_start(date(2004, 8, 19))
        datetime.date(2004, 8, 16)
        >>> week_start(date(2004, 8, 15))
        datetime.date(2004, 8, 9)
        >>> week_start(date(2004, 8, 14))
        datetime.date(2004, 8, 9)
        >>> week_start(date(2004, 8, 21))
        datetime.date(2004, 8, 16)
        >>> week_start(date(2004, 8, 22))
        datetime.date(2004, 8, 16)
        >>> week_start(date(2004, 8, 23))
        datetime.date(2004, 8, 23)

    Assuming that week starts on Sundays:

        >>> import calendar
        >>> week_start(date(2004, 8, 19), calendar.SUNDAY)
        datetime.date(2004, 8, 15)
        >>> week_start(date(2004, 8, 15), calendar.SUNDAY)
        datetime.date(2004, 8, 15)
        >>> week_start(date(2004, 8, 14), calendar.SUNDAY)
        datetime.date(2004, 8, 8)
        >>> week_start(date(2004, 8, 21), calendar.SUNDAY)
        datetime.date(2004, 8, 15)
        >>> week_start(date(2004, 8, 22), calendar.SUNDAY)
        datetime.date(2004, 8, 22)
        >>> week_start(date(2004, 8, 23), calendar.SUNDAY)
        datetime.date(2004, 8, 22)

    """
    assert 0 <= first_day_of_week < 7
    delta = date.weekday() - first_day_of_week
    if delta < 0:
        delta += 7
    return date - timedelta(delta)

def weeknum_bounds(year, weeknum):
    """Calculates the inclusive date bounds for a (year, weeknum) tuple.
    """
    # The first week of a year is at least 4 days long, so January 4th
    # is in the first week.
    firstweek = week_start(date(year, 1, 4), calendar.MONDAY)
    # move forward to the right week number
    weekstart = firstweek + timedelta(weeks=weeknum-1)
    weekend = weekstart + timedelta(days=6)
    return (weekstart, weekend)

def check_weeknum(year, weeknum):
    """Checks to see whether a (year, weeknum) tuple refers to a real
    ISO week number."""
    weekstart, weekend = weeknum_bounds(year, weeknum)
    isoyear, isoweek, isoday = weekstart.isocalendar()
    return (year, weeknum) == (isoyear, isoweek)

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

class DayView(CalendarView):
    """A day view of the calendar."""
    implements(ICalendarDayView)

    def __init__(self, calendar, year, month, day):
        self.day = date(year, month, day)
        CalendarView.__init__(self, calendar,
                              '%04d-%02d-%02d' % (year, month, day))

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

    def __init__(self, calendar, year, week):
        assert check_weeknum(year, week), 'invalid week number'
        CalendarView.__init__(self, calendar, '%04d-W%02d' % (year, week))
        self.year = year
        self.week = week
        self.bounds = weeknum_bounds(year, week)

        # navigation links
        (isoyear, isoweek, isoday) = (self.bounds[0] - timedelta(days=1)).isocalendar()
        self.prevURL = '../%04d-W%02d' % (isoyear, isoweek)
        (isoyear, isoweek, isoday) = (self.bounds[1] + timedelta(days=1)).isocalendar()
        self.nextURL = '../%04d-W%02d' % (isoyear, isoweek)

        self._setViewURLs(self.bounds[0])

class MonthView(CalendarView):
    """A month view of the calendar."""
    implements(ICalendarMonthView)

    def __init__(self, calendar, year, month):
        assert 1 <= month <= 12, 'invalid month number'
        CalendarView.__init__(self, calendar, '%04d-%02d' % (year, month))
        self.year = year
        self.month = month
        start = date(year, month, 1)
        self.bounds = [start, next_month(start) - timedelta(days=1)]

        # navigation links
        prev = prev_month(start)
        self.prevURL = '../%04d-%02d' % (prev.year, prev.month)
        next = next_month(start)
        self.nextURL = '../%04d-%02d' % (next.year, next.month)

        self._setViewURLs(start)

class YearView(CalendarView):
    """A month view of the calendar."""
    implements(ICalendarYearView)

    def __init__(self, calendar, year):
        CalendarView.__init__(self, calendar, '%04d' % year)
        self.year = year
        start = date(year, 1, 1)
        end = date(year+1, 1, 1) - timedelta(days=1)
        self.bounds = [start, end]

        # navigation links
        self.prevURL = '../%04d' % (year - 1)
        self.nextURL = '../%04d' % (year + 1)

        self._setViewURLs(start)
