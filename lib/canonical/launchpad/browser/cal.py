# Copyright 2005 Canonical Ltd

# XXX mpt 2006-09-14: All Calendar pages should return HTTP 410 Gone.

__metaclass__ = type

__all__ = [
    'CalendarTraversalMixin',
    'CalendarNavigation',
    'CalendarEventSetNavigation',
    'CalendarDay',
    'CalendarWeek',
    'CalendarMonth',
    'CalendarYear',
    'CalendarView',
    'CalendarContextMenu',
    'CalendarAppMenu',
    'CalendarRangeAppMenu',
    'CalendarDayView',
    'CalendarWeekView',
    'CalendarMonthView',
    'CalendarYearView',
    'CalendarEventAddView',
    'CalendarCreateView',
    'CalendarSubscriptionsView',
    'CalendarSubscribeView',
    'CalendarInfoPortletView',
    ]

import re
import calendar
import operator
from datetime import datetime, date, timedelta

import pytz

from sqlobject import SQLObjectNotFound

from zope.interface import implements
from zope.component import getUtility
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.form.browser.add import AddView

from schoolbell.interfaces import IEditCalendar, ICalendar
from schoolbell.utils import (
    prev_month, next_month, weeknum_bounds, Slots)
from schoolbell.simple import SimpleCalendarEvent

from canonical.launchpad import _
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.interfaces import (
     ICalendarDay, ICalendarWeek, ICalendarOwner, ILaunchpadCalendar,
     ICalendarMonth, ICalendarYear, ICalendarSet, ICalendarEventSet,
     ICalendarSubscriptionSubset, ICalendarRange, ILaunchBag)
from canonical.launchpad.webapp import (
    ApplicationMenu, ContextMenu, Link, canonical_url, Navigation,
    GetitemNavigation, stepto)


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

colours = [
    { 'code': '#ffffff', 'name': _('White') },
    { 'code': '#c0ffc8', 'name': _('Green') },
    { 'code': '#c0d0ff', 'name': _('Blue') },
    { 'code': '#e0d0ff', 'name': _('Purple') },
    { 'code': '#faffd2', 'name': _('Yellow') },
    { 'code': '#c1c1c1', 'name': _('Grey') },
    ]

UTC = pytz.timezone('UTC')


class CalendarTraversalMixin:
    """Mixin class for use in Navigation classes where you can traverse to
    +calendar.
    """

    @stepto('+calendar')
    def calendar(self):
        return ICalendarOwner(self.context).calendar


class CalendarNavigation(Navigation):
    """Navigation handling for Calendars.

    The calendar URL space is as follows:
      .../2005-04-01 -- day view for 2005-04-01
      .../2005-W01   -- week view for first ISO week of 2005
      .../2005-04    -- month view for April, 2005
      .../2005       -- year view for 2005
      .../today      -- day view for today (for easy bookmarking)
      .../this-week  -- week view for this week
      .../this-month -- month view for this month
      .../this-year  -- year view for this year
      .../events     -- events set for this calendar
    """

    usedfor = ICalendar

    _year_pat  = re.compile(r'^(\d\d\d\d)$')
    _month_pat = re.compile(r'^(\d\d\d\d)-(\d\d)$')
    _week_pat  = re.compile(r'^(\d\d\d\d)-W(\d\d)$')
    _day_pat   = re.compile(r'^(\d\d\d\d)-(\d\d)-(\d\d)$')

    def traverse(self, name):
        """Traverse sub-URLs of an ICalendar

        If the URL does not match one of these names, None is returned.
        """
        match = self._year_pat.match(name)
        if match:
            try:
                return CalendarYear(self.context,
                                    date(int(match.group(1)), 1, 1))
            except ValueError:
                return None
        match = self._month_pat.match(name)
        if match:
            try:
                return CalendarMonth(self.context,
                                     date(int(match.group(1)),
                                          int(match.group(2)),
                                          1))
            except ValueError:
                return None
        match = self._week_pat.match(name)
        if match:
            try:
                start, end = weeknum_bounds(int(match.group(1)),
                                            int(match.group(2)))
                return CalendarWeek(self.context, start)
            except ValueError:
                return None
        match = self._day_pat.match(name)
        if match:
            try:
                return CalendarDay(self.context,
                                   date(int(match.group(1)),
                                        int(match.group(2)),
                                        int(match.group(3))))
            except ValueError:
                return None
        return None

    @property
    def _datetimenow(self):
        user_timezone = getUtility(ILaunchBag).timezone
        return datetime.now(user_timezone)

    @stepto('today')
    def today(self):
        return CalendarDay(self.context, self._datetimenow)

    @stepto('this-week')
    def thisweek(self):
        return CalendarWeek(self.context, self._datetimenow)

    @stepto('this-month')
    def thismonth(self):
        return CalendarMonth(self.context, self._datetimenow)

    @stepto('this-year')
    def thisyear(self):
        return CalendarYear(self.context, self._datetimenow)

    @stepto('events')
    def events(self):
        return getUtility(ICalendarEventSet)


class CalendarEventSetNavigation(GetitemNavigation):

    usedfor = ICalendarEventSet


class CalendarDay:
    implements(ICalendarDay)

    def __init__(self, calendar, day):
        self.calendar = calendar
        self.name = '%04d-%02d-%02d' % (day.year, day.month, day.day)
        self.date = day
        self.year = day.year
        self.month = day.month
        self.day = day.day

        user_timezone = getUtility(ILaunchBag).timezone
        self.start = datetime(day.year, day.month, day.day,
                              0, 0, 0, 0, user_timezone).astimezone(UTC)
        self.end = self.start + timedelta(days=1)

    @property
    def prevRange(self):
        return CalendarDay(self.calendar, self.date - timedelta(days=1))

    @property
    def nextRange(self):
        return CalendarDay(self.calendar, self.date + timedelta(days=1))

class CalendarWeek:
    implements(ICalendarWeek)

    def __init__(self, calendar, day):
        self.calendar = calendar
        self.date = day
        self.year, self.week, dummy = day.isocalendar()
        self.name = '%04d-W%02d' % (self.year, self.week)

        user_timezone = getUtility(ILaunchBag).timezone
        start, end = weeknum_bounds(self.year, self.week)
        self.start = datetime(start.year, start.month, start.day,
                              0, 0, 0, 0, user_timezone).astimezone(UTC)
        self.end = self.start + timedelta(weeks=1)

    @property
    def prevRange(self):
        return CalendarWeek(self.calendar, self.date - timedelta(days=7))

    @property
    def nextRange(self):
        return CalendarWeek(self.calendar, self.date + timedelta(days=7))


class CalendarMonth:
    implements(ICalendarMonth)

    def __init__(self, calendar, day):
        self.calendar = calendar
        self.date = day
        self.name = '%04d-%02d' % (day.year, day.month)
        self.year = day.year
        self.month = day.month

        user_timezone = getUtility(ILaunchBag).timezone
        self.start = datetime(day.year, day.month, 1,
                              0, 0, 0, 0, user_timezone).astimezone(UTC)
        next = next_month(day)
        self.end = datetime(next.year, next.month, 1,
                            0, 0, 0, 0, user_timezone).astimezone(UTC)

    @property
    def prevRange(self):
        day = prev_month(self.date)
        return CalendarMonth(self.calendar, day)

    @property
    def nextRange(self):
        day = next_month(self.date)
        return CalendarMonth(self.calendar, day)


class CalendarYear:
    implements(ICalendarYear)

    def __init__(self, calendar, day):
        self.calendar = calendar
        self.date = day
        self.name = '%04d' % day.year
        self.year = day.year

        user_timezone = getUtility(ILaunchBag).timezone
        self.start = datetime(day.year, 1, 1,
                              0, 0, 0, 0, user_timezone).astimezone(UTC)
        self.end = datetime(day.year + 1, 1, 1,
                            0, 0, 0, 0, user_timezone).astimezone(UTC)

    @property
    def prevRange(self):
        day = date(self.date.year - 1, self.date.month, self.date.day)
        return CalendarYear(self.calendar, day)

    @property
    def nextRange(self):
        day = date(self.date.year + 1, self.date.month, self.date.day)
        return CalendarYear(self.calendar, day)


class CalendarView:
    """View class for ICalendar (when not displaying a particular date
    range)
    """
    __used_for__ = ICalendar

    def __init__(self, context, request):
        self.context = context
        self.request = request

        user_timezone = getUtility(ILaunchBag).timezone
        now = datetime.now(user_timezone)

        events = self.context.expand(now, now + timedelta(days=14))
        self.events = shortlist(events)
        self.events.sort(key=operator.attrgetter('dtstart'))


class CalendarContextMenu(ContextMenu):

    usedfor = ICalendar
    links = ['addevent', 'subscribe']

    def addevent(self):
        text = 'Add event'
        return Link('+add', text, icon='add')

    def subscribe(self):
        # The merged calendar view at "/calendar" is not stored in the
        # database, so has no ID.  Therefore, it can't be subscribed to,
        # so we leave out the link.
        enabled = (self.context.id is not None)
        text = 'Subscribe to this calendar'
        return Link('+subscribe', text, icon='edit', enabled=enabled)


class CalendarAppMenu(ApplicationMenu):
    """Application menus for the base calendar view.

    The application menus take you to the day, week, month and year
    views corresponding to a particular date.

    In the case of the base calendar view, the date used is 'now' in
    the user's preferred time zone.
    """

    usedfor = ICalendar
    links = ['day', 'week', 'month', 'year']
    facet = 'calendar'

    def __init__(self, context, date=None):
        self.context = context
        if date is not None:
            self.date = date
        else:
            user_timezone = getUtility(ILaunchBag).timezone
            self.date = datetime.now(user_timezone)

    def day(self):
        target =  canonical_url(CalendarDay(self.context, self.date))
        text = 'Day'
        return Link(target, text)

    def week(self):
        target = canonical_url(CalendarWeek(self.context, self.date))
        text = 'Week'
        return Link(target, text)

    def month(self):
        target =  canonical_url(CalendarMonth(self.context, self.date))
        text = 'Month'
        return Link(target, text)

    def year(self):
        target =  canonical_url(CalendarYear(self.context, self.date))
        text = 'Year'
        return Link(target, text)


class CalendarRangeAppMenu(CalendarAppMenu):
    """Application menus for the various calendar date range views.

    The date used for the links comes from the current date range
    being displayed.
    """

    usedfor = ICalendarRange

    def __init__(self, context):
        CalendarAppMenu.__init__(self,
                                  context.calendar,
                                  context.date)


class CalendarViewBase:

    def __init__(self, context, request, datestring):
        self.context = context
        self.request = request
        self.datestring = datestring
        self.user_timezone = getUtility(ILaunchBag).timezone
        user = getUtility(ILaunchBag).user
        if user is not None:
            self.subscriptions = ICalendarSubscriptionSubset(user)
        else:
            self.subscriptions = None

        # get the events occurring within the given time range
        self.events = shortlist(context.calendar.expand(context.start,
                                                        context.end))
        self.events.sort()

    def eventColour(self, event):
        if self.subscriptions is not None:
            return self.subscriptions.getColour(event.calendar)
        else:
            # XXX James Henstridge 2005-07-11:
            # This is replicating a constant from database/cal.py
            # This won't be necessary once CalendarAggregation is
            # implemented.
            return '#efefef'

    def eventStart(self, event):
        dtstart = event.dtstart.astimezone(self.user_timezone)
        return dtstart.strftime('%H:%M')

    def eventStartDate(self, event):
        dtstart = event.dtstart.astimezone(self.user_timezone)
        return dtstart.strftime('%Y-%m-%d')

    def eventEnd(self, event):
        dtend = (event.dtstart + event.duration).astimezone(self.user_timezone)
        return dtend.strftime('%H:%M')


class MonthInfo:
    def __init__(self, year, month):
        self.monthname = monthnames[month-1]
        self.monthURL = '../%04d-%02d' % (year, month)
        self.days = []
        dummy, num_days = calendar.monthrange(year, month)
        for i in range(num_days):
            self.days.append(DayInfo(date(year, month, i+1)))
        self.layout = calendar.monthcalendar(year, month)


class DayInfo:
    def __init__(self, date):
        self.date = date
        self.dayname = '%s, %d %s' % (daynames[self.date.weekday()],
                                      self.date.day,
                                      monthnames[self.date.month - 1])
        self.dayURL = '../%04d-%02d-%02d' % (date.year,
                                             date.month,
                                             date.day)
        self.addURL = ('../+add?field.dtstart=%04d-%02d-%02d%%2008:00:00' %
                       (date.year, date.month, date.day))
        self.events = []

    @property
    def hasEvents(self):
        return len(self.events) != 0


class CalendarDayView(CalendarViewBase):
    __used_for__ = ICalendarDay

    # XXX James Henstridge 2005-06-28:
    # The layout logic in this view is adapted from the Schooltool
    # day view code in DailyCalendarView (src/schooltool/browser/cal.py)
    # Ideally the common layout code should be in the schoolbell/ module.

    starthour = 8
    endhour = 19

    def __init__(self, context, request):
        CalendarViewBase.__init__(self, context, request,
                                  '%d %s %04d' % (context.day,
                                                  monthnames[context.month-1],
                                                  context.year))

        self._setRange()
        self.visiblehours = self.endhour - self.starthour

    def getColumns(self):
        """Return the maximum number of events that are overlapping.

        Extends the event so that start and end times fall on hour
        boundaries before calculating overlaps.
        """
        width = [0] * 24
        daystart = datetime(self.context.year, self.context.month,
                            self.context.day, 0, 0, 0, 0,
                            self.user_timezone)
        for event in self.events:
            t = daystart
            dtend = daystart + timedelta(days=1)
            for title, start, duration in self.calendarRows():
                if start <= event.dtstart < start + duration:
                    t = start
                if start < event.dtstart + event.duration <= start + duration:
                    dtend = start + duration
            while True:
                width[t.hour] += 1
                t += timedelta(hours=1)
                if t >= dtend:
                    break
        return max(width) or 1

    def _setRange(self):
        """Set the starthour and endhour attributes according to events.

        The range of hours to display is the union of the range
        08:00-18:00 and time spans of all the events in the events
        list.
        """
        midnight = datetime(self.context.year, self.context.month,
                            self.context.day, 0, 0, 0, 0,
                            self.user_timezone)
        for event in self.events:
            start = midnight + timedelta(hours=self.starthour)
            end = midnight + timedelta(hours=self.endhour)
            if event.dtstart < start:
                newstart = max(midnight, event.dtstart)
                self.starthour = newstart.astimezone(self.user_timezone).hour

            if event.dtstart + event.duration > end:
                newend = min(midnight + timedelta(days=1),
                             event.dtstart + event.duration +
                             timedelta(seconds=3599))
                self.endhour = newend.astimezone(self.user_timezone).hour
                if self.endhour == 0:
                    self.endhour = 24

    def calendarRows(self):
        """Iterates over (title, start, duration) of time slots that
        make up the daily calendar.
        """
        rows = []
        for hour in range(self.starthour, self.endhour):
            rows.append(('%02d:00' % hour,
                         datetime(self.context.year, self.context.month,
                                  self.context.day, hour, 0, 0, 0,
                                  self.user_timezone),
                         timedelta(hours=1)))
        return rows

    def getHours(self):
        """Return an iterator over the rows of the table.

        Every row is a dict with the following keys:

            'time' -- row label (e.g. 8:00)
            'cols' -- sequence of cell values for this row

        A cell value can be one of the following:
            None  -- if there is no event in this cell
            event -- if an event starts in this cell
            ''    -- if an event started above this cell

        """
        nr_cols = self.getColumns()
        events = self.events[:]
        self._setRange()
        slots = Slots()
        for title, start, duration in self.calendarRows():
            end = start + duration
            hour = start.hour

            # Remove the events that have already ended
            for i in range(nr_cols):
                ev = slots.get(i, None)
                if ev is not None and ev.dtstart + ev.duration <= start:
                    del slots[i]

            # Add events that start during (or before) this hour
            while events and events[0].dtstart < end:
                event = events.pop(0)
                slots.add(event)
            cols = []

            # Format the row
            for i in range(nr_cols):
                ev = slots.get(i, None)
                if (ev is not None and
                    ev.dtstart < start and
                    hour != self.starthour):
                    # The event started before this hour (except first row)
                    cols.append('')
                else:
                    # Either None, or new event
                    cols.append(ev)
            yield { 'title': title, 'cols': tuple(cols),
                    'time': start.strftime("%H:%M"),
                    'addURL': '../+add?field.dtstart=%s' %
                              start.strftime('%Y-%m-%d%%20%H:%M'),
                    'duration': duration.seconds // 60 }

    def rowspan(self, event):
        """Calculate how many calendar rows the event will take today."""
        count = 0
        for title, start, duration in self.calendarRows():
            if (start < event.dtstart + event.duration and
                event.dtstart < start + duration):
                count += 1
        return count

    def eventTop(self, event):
        """Calculate the position of the top of the event block in the
        display.

        Each hour is made up of 4 units ('em' currently).  If an event
        starts at 10:15, and the day starts at 8:00 we get a top value
        of:

          (2 * 4) + (15 / 15) = 9

        """
        daystart = datetime(self.context.year, self.context.month,
                            self.context.day, 0, 0, 0, 0, self.user_timezone)
        dtstart = max(event.dtstart.astimezone(self.user_timezone), daystart)
        top = ((dtstart.hour - self.starthour) * 4
               + dtstart.minute / 15)
        return top

    def eventHeight(self, event):
        """Calculate the height of the event block in the display.

        Each hour is made up of 4 units ('em' currently).  Need to round 1 -
        14 minute intervals up to 1 display unit.
        """
        daystart = datetime(self.context.year, self.context.month,
                            self.context.day, 0, 0, 0, 0, self.user_timezone)
        dayend = daystart + timedelta(days=1)

        duration = (min(dayend, event.dtstart + event.duration) -
                    max(daystart, event.dtstart))
        minutes = (duration.days * 1440) + (duration.seconds / 60)

        return max(1, (minutes + 14) / 15)


class CalendarWeekView(CalendarViewBase):
    """A week view of the calendar."""
    __used_for__ = ICalendarWeek

    # the layout of the days in the week view.  The rowspans list says
    # describes how many rows in the table each day should span.  In
    # this configuration, day 5 spans to fill the bottom left cell of
    # the table.
    layout = [[1, 2],
              [3, 4],
              [5, 6],
              [0, 7]]
    rowspans = [None, None, None, None, 2, None, None]

    def __init__(self, context, request):
        CalendarViewBase.__init__(self, context, request,
                          _('Week %d, %04d') % (context.week, context.year))

        start, end = weeknum_bounds(context.year, context.week)

        self.days = []
        for i in range(7):
            day = DayInfo(start + timedelta(days=i))
            self.days.append(day)

        # find events for the week
        for event in self.events:
            dtstart = event.dtstart.astimezone(self.user_timezone)
            self.days[dtstart.weekday()].events.append(event)


class CalendarMonthView(CalendarViewBase):
    """A month view of the calendar."""
    __used_for__ = ICalendarMonth

    daynames = daynames

    def __init__(self, context, request):
        datestring = '%s %04d' % (monthnames[context.month - 1], context.year)
        CalendarViewBase.__init__(self, context, request, datestring)

        # create dayinfo instances for each day of the month
        self.days = []
        dummy, num_days = calendar.monthrange(context.year, context.month)
        for i in range(num_days):
            self.days.append(DayInfo(date(context.year, context.month, i+1)))

        for event in self.events:
            dtstart = event.dtstart.astimezone(self.user_timezone)
            # skip events that spans over the next month to prevent
            # dtstart.day - 1 be out of range.
            if dtstart < context.start:
                continue
            self.days[dtstart.day - 1].events.append(event)

        # lay out the dayinfo objects in a 2D grid
        self.layout = calendar.monthcalendar(context.year, context.month)


class CalendarYearView(CalendarViewBase):
    """A year view of the calendar."""
    __used_for__ = ICalendarYear

    def __init__(self, context, request):
        CalendarViewBase.__init__(self, context, request,
                                  '%04d' % context.year)

        self.months = []
        for month in range(1, 13):
            self.months.append(MonthInfo(context.year, month))

        for event in self.events:
            dtstart = event.dtstart.astimezone(self.user_timezone)
            dayinfo = self.months[dtstart.month - 1].days[dtstart.day - 1]
            dayinfo.events.append(event)

        self.daynames = [d[0] for d in daynames]
        self.layout = [[ 1,  2,  3],
                       [ 4,  5,  6],
                       [ 7,  8,  9],
                       [10, 11, 12]]


class CalendarEventAddView(AddView):

    __used_for__ = IEditCalendar

    _nextURL = '.'

    def createAndAdd(self, data):
        """Create a new calendar event.

        `data` is a dictionary with the data entered in the form.
        """
        calendar = self.context
        kw = dict([(str(k), v) for k, v in data.items()])
        event = SimpleCalendarEvent(**kw)
        calendar.addEvent(event)
        notify(ObjectCreatedEvent(event))

        dtstart = event.dtstart.astimezone(
            getUtility(ILaunchBag).timezone)
        self._nextURL = canonical_url(CalendarWeek(calendar, dtstart))

    def nextURL(self):
        return self._nextURL

class CalendarCreateView:
    __used_for__ = ICalendarOwner

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        if self.request.method != "POST":
            raise RuntimeError("This form must be posted!")

        calendar = ICalendarOwner(self.context).getOrCreateCalendar()
        if not calendar:
            raise RuntimeError("Could not create calendar")
        self.request.response.redirect('+calendar')


class CalendarSubscriptionsView:
    colours = colours

    def __init__(self, context, request):
        self.context = context
        self.request = request
        user = getUtility(ILaunchBag).user
        self._subscriptions = ICalendarSubscriptionSubset(user)

    def subscriptions(self):
        """Returns information about all the user's calendar
        subscriptions.  This is used to build the list of calendars
        for the user to subscribe or unsubscribe from.
        """
        # XXX jamesh 2005-01-25:
        # Should make sure that calendars for person and teams they
        # are a member of are always in the subscription list.
        for cal in self._subscriptions:
            yield { 'calendar': cal,
                    'subscribed': True,
                    'colour': self._subscriptions.getColour(cal) }

    def submit(self):
        if 'UPDATE_SUBMIT' in self.request.form:
            if self.request.method != "POST":
                raise RuntimeError("This form must be posted!")

            subscriptions = [(int(key[4:]), value)
                             for key, value in self.request.form.items()
                             if re.match(r'sub.\d+', key)]
            for calendarid, value in subscriptions:
                try:
                    calendar = getUtility(ICalendarSet)[calendarid]
                except SQLObjectNotFound:
                    raise RuntimeError(
                        "Unknown calendar ID found in submitted form data")
                if value != 'no':
                    self._subscriptions.subscribe(calendar)
                else:
                    self._subscriptions.unsubscribe(calendar)

                colour = self.request.get('colour.%d' % calendarid, None)
                if colour:
                    self._subscriptions.setColour(calendar, colour)


class CalendarSubscribeView:
    colours = colours

    def __init__(self, context, request):
        self.context = ILaunchpadCalendar(context)
        self.request = request

    def setUpUserSubscriptions(self):
        user = getUtility(ILaunchBag).user
        self._subscriptions = ICalendarSubscriptionSubset(user)

    def isSubscribed(self):
        return self.context in self._subscriptions

    def colour(self):
        return self._subscriptions.getColour(self.context)

    def submit(self):
        if 'UPDATE_SUBMIT' in self.request.form:
            if self.request.method != "POST":
                raise RuntimeError("This form must be posted!")

            if self.request.form.get('subscribe', None) != 'no':
                self._subscriptions.subscribe(self.context)
            else:
                self._subscriptions.unsubscribe(self.context)
            colour = self.request.get('colour')
            if colour:
                self._subscriptions.setColour(self.context, colour)


class CalendarInfoPortletView:
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.calendar = ICalendarOwner(context).calendar

        self.user_timezone = getUtility(ILaunchBag).timezone
        now = datetime.now(self.user_timezone)

        self.month ='%s %04d' % (monthnames[now.month-1], now.year)


        # create array of day information for each day of the month
        self.daynames = [d[0] for d in daynames]
        self.days = []
        dummy, num_days = calendar.monthrange(now.year, now.month)
        for i in range(num_days):
            dayURL = '+calendar/%04d-%02d-%02d' % (now.year, now.month, i+1)
            self.days.append({ 'day': i+1,
                               'dayURL': dayURL,
                               'hasEvents': False })

        # convert to UTC time offsets
        start = date(now.year, now.month, 1)
        end = next_month(start)
        start = datetime(start.year, start.month, 1,
                         0, 0, 0, 0, self.user_timezone).astimezone(UTC)
        end = datetime(end.year, end.month, 1,
                         0, 0, 0, 0, self.user_timezone).astimezone(UTC)

        if self.calendar:
            for event in self.calendar.expand(start, end):
                dtstart = event.dtstart.astimezone(self.user_timezone)
                # skip events that spans over the next month to prevent
                # dtstart.day - 1 be out of range.
                if dtstart < start:
                    continue
                self.days[dtstart.day - 1]['hasEvents'] = True

        # lay out the dayinfo objects in a 2D grid
        self.layout = calendar.monthcalendar(now.year, now.month)

        self.canSubscribe = getUtility(ILaunchBag).user is not None
