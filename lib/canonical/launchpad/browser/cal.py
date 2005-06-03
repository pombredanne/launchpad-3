
import re
import calendar
from datetime import datetime, date, timedelta, tzinfo

import pytz

from sqlobject import SQLObjectNotFound

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from zope.interface import implements
from zope.component import getUtility
from zope.event import notify
from zope.security import checkPermission
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.form.browser.add import AddView
from zope.app.pagetemplate.viewpagetemplatefile import \
     ViewPageTemplateFile, BoundPageTemplate
from canonical.launchpad.browser.editview import SQLObjectEditView

from schoolbell.interfaces import IEditCalendar, ICalendarEvent
from schoolbell.simple import SimpleCalendarEvent
from canonical.launchpad.interfaces import \
     IPerson, ICalendarDay, ICalendarWeek, ICalendarOwner, \
     ILaunchpadCalendar, ICalendarMonth, ICalendarYear, \
     ICalendarEventCollection, ILaunchBag

from canonical.launchpad.database import Calendar, CalendarEvent
from canonical.launchpad.components.cal import CalendarSubscriptionSet

from schoolbell.utils import prev_month, next_month
from schoolbell.utils import weeknum_bounds, check_weeknum
from schoolbell.utils import Slots

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

# XXXX we don't actually have any of these view classes yet ...
_year_pat  = re.compile(r'^(\d\d\d\d)$')
_month_pat = re.compile(r'^(\d\d\d\d)-(\d\d)$')
_week_pat  = re.compile(r'^(\d\d\d\d)-W(\d\d)$')
_day_pat   = re.compile(r'^(\d\d\d\d)-(\d\d)-(\d\d)$')
def traverseCalendar(calendar, request, name):
    user_timezone = getUtility(ILaunchBag).timezone

    match = _year_pat.match(name)
    if match:
        try:
            return CalendarYear(calendar,
                                year=int(match.group(1)))
        except ValueError:
            return None
    match = _month_pat.match(name)
    if match:
        try:
            return CalendarMonth(calendar,
                                 year=int(match.group(1)),
                                 month=int(match.group(2)))
        except ValueError:
            return None
    match = _week_pat.match(name)
    if match:
        try:
            return CalendarWeek(calendar,
                                year=int(match.group(1)),
                                week=int(match.group(2)))
        except ValueError:
            return None
    match = _day_pat.match(name)
    if match:
        try:
            return CalendarDay(calendar,
                               year=int(match.group(1)),
                               month=int(match.group(2)),
                               day=int(match.group(3)))
        except ValueError:
            return None
    now = datetime.now(user_timezone)
    if name == 'today':
        return CalendarDay(calendar,
                           year=now.year,
                           month=now.month,
                           day=now.day)
    elif name == 'this-week':
        isoyear, isoweek, isoday = now.isocalendar()
        return CalendarWeek(calendar,
                            year=isoyear,
                            week=isoweek)
    elif name == 'this-month':
        return CalendarMonth(calendar,
                             year=now.year,
                             month=now.month)
    elif name == 'this-year':
        return CalendarYear(calendar,
                            year=now.year)
    elif name == 'events':
        return CalendarEventCollection(calendar)

class CalendarDay(object):
    implements(ICalendarDay)

    def __init__(self, calendar, year, month, day):
        # this will raise an error for invalid dates ...
        date(year, month, day)
        self.calendar = calendar
        self.year = year
        self.month = month
        self.day = day

class CalendarWeek(object):
    implements(ICalendarWeek)

    def __init__(self, calendar, year, week):
        # this will raise an error for invalid dates ...
        if not check_weeknum(year, week):
            raise ValueError, 'invalid week number'
        self.calendar = calendar
        self.year = year
        self.week = week

class CalendarMonth(object):
    implements(ICalendarMonth)

    def __init__(self, calendar, year, month):
        # this will raise an error for invalid dates ...
        date(year, month, 1)
        self.calendar = calendar
        self.year = year
        self.month = month

class CalendarYear(object):
    implements(ICalendarYear)

    def __init__(self, calendar, year):
        # this will raise an error for invalid dates ...
        date(year, 1, 1)
        self.calendar = calendar
        self.year = year

class CalendarViewBase(object):

    def __init__(self, context, request, datestring):
        self.context = context
        self.request = request
        self.datestring = datestring
        self.user_timezone = getUtility(ILaunchBag).timezone
        self.canAddEvents = checkPermission('launchpad.Edit', context.calendar)
        person = IPerson(request.principal, None)
        if person:
            self.subscriptions = CalendarSubscriptionSet(person)
        else:
            self.subscriptions = None

    def _setViewURLs(self, date):
        """Computes the URLs used to switch calendar views."""
        self.dayViewURL = '../%04d-%02d-%02d' % (date.year,
                                                 date.month,
                                                 date.day)
        (isoyear, isoweek, isoday) = date.isocalendar()
        self.weekViewURL = '../%04d-W%02d' % (isoyear, isoweek)
        self.monthViewURL = '../%04d-%02d' % (date.year, date.month)
        self.yearViewURL = '../%04d' % date.year

    def eventColour(self, event):
        if self.subscriptions:
            return self.subscriptions.getColour(event.calendar)
        else:
            return '#9db8d2'
    def eventStart(self, event):
        dtstart = event.dtstart.astimezone(self.user_timezone)
        return dtstart.strftime('%H:%M')
    def eventStartDate(self, event):
        dtstart = event.dtstart.astimezone(self.user_timezone)
        return dtstart.strftime('%Y-%m-%d')
    def eventEnd(self, event):
        dtend = (event.dtstart + event.duration).astimezone(self.user_timezone)
        return dtend.strftime('%H:%M')

class MonthInfo(object):
    def __init__(self, year, month):
        self.monthname = monthnames[month-1]
        self.monthURL = '../%04d-%02d' % (year, month)
        self.days = []
        for i in range(calendar.monthrange(year, month)[1]):
            self.days.append(DayInfo(date(year, month, i+1)))
        self.layout = calendar.monthcalendar(year, month)

class DayInfo(object):
    def __init__(self, date):
        self.date = date
        self.dayname = '%s, %d %s' % (daynames[self.date.weekday()],
                                      self.date.day,
                                      monthnames[self.date.month - 1])
        self.dayURL = '../%04d-%02d-%02d' % (date.year,
                                             date.month,
                                             date.day)
        self.addURL = '../+add?field.dtstart=%04d-%02d-%02d%%2008:00:00' % \
                      (date.year, date.month, date.day)
        self.events = []
    def hasEvents(self):
        return len(self.events) != 0
    hasEvents = property(hasEvents)


class CalendarDayView(CalendarViewBase):
    __used_for__ = ICalendarDay

    starthour = 8
    endhour = 19

    def __init__(self, context, request):
        CalendarViewBase.__init__(self, context, request,
                                  '%d %s %04d' % (context.day,
                                                  monthnames[context.month-1],
                                                  context.year))

        day = date(context.year, context.month, context.day)
        yesterday = day - timedelta(days=1)
        self.prevURL = '../%04d-%02d-%02d' % (yesterday.year,
                                              yesterday.month,
                                              yesterday.day)
        tomorrow = day + timedelta(days=1)
        self.nextURL = '../%04d-%02d-%02d' % (tomorrow.year,
                                              tomorrow.month,
                                              tomorrow.day)
        self._setViewURLs(day)

        start = datetime(context.year, context.month, context.day,
                         0, 0, 0, 0, self.user_timezone).astimezone(UTC)
        end = start + timedelta(days=1)

        self.events = list(context.calendar.expand(start, end))
        self.events.sort()
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
            dtend = daystart + timedelta(1)
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
                             event.dtstart+event.duration + timedelta(0, 3599))
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

    def __init__(self, context, request):
        CalendarViewBase.__init__(self, context, request,
                          _('Week %d, %04d') % (context.week, context.year))

        (start, end) = weeknum_bounds(context.year, context.week)

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

        # find events for the week
        self.events = []
        start = datetime(start.year, start.month, start.day,
                         0, 0, 0, 0, self.user_timezone).astimezone(UTC)
        end = start + timedelta(weeks=1)
        for event in context.calendar.expand(start, end):
            dtstart = event.dtstart.astimezone(self.user_timezone)
            self.days[dtstart.weekday()].events.append(event)

        self.layout = [ [ 1, 2 ],
                        [ 3, 4 ],
                        [ 5, 6 ],
                        [ 0, 7 ] ]
        self.rowspans = [ None, None, None, None, 2, None, None ]

        # self.layout = [[ 1, 2, 3, 4, 5, 6, 7 ]]
        # self.rowspans = [ None, None, None, None, None, None, None ]

class CalendarMonthView(CalendarViewBase):
    """A month view of the calendar."""
    __used_for__ = ICalendarMonth

    daynames = daynames

    def __init__(self, context, request):
        datestring = '%s %04d' % (monthnames[context.month-1], context.year)
        CalendarViewBase.__init__(self, context, request, datestring)
        start = date(context.year, context.month, 1)

        # navigation links
        prev = prev_month(start)
        self.prevURL = '../%04d-%02d' % (prev.year, prev.month)
        next = next_month(start)
        self.nextURL = '../%04d-%02d' % (next.year, next.month)
        self._setViewURLs(start)

        # create dayinfo instances for each day of the month
        self.days = []
        for i in range(calendar.monthrange(context.year, context.month)[1]):
            self.days.append(DayInfo(date(context.year, context.month, i+1)))

        # convert to UTC time offsets
        start = datetime(start.year, start.month, 1,
                         0, 0, 0, 0, self.user_timezone).astimezone(UTC)
        end = datetime(next.year, next.month, 1,
                         0, 0, 0, 0, self.user_timezone).astimezone(UTC)

        for event in context.calendar.expand(start, end):
            dtstart = event.dtstart.astimezone(self.user_timezone)
            self.days[dtstart.day - 1].events.append(event)

        # lay out the dayinfo objects in a 2D grid
        self.layout = calendar.monthcalendar(context.year, context.month)

class CalendarYearView(CalendarViewBase):
    """A month view of the calendar."""
    __used_for__ = ICalendarYear

    def __init__(self, context, request):
        CalendarViewBase.__init__(self, context, request, '%04d'%context.year)
        start = date(context.year, 1, 1)
        end = date(context.year+1, 1, 1) - timedelta(days=1)
        self.bounds = [start, end]

        # navigation links
        self.prevURL = '../%04d' % (context.year - 1)
        self.nextURL = '../%04d' % (context.year + 1)

        self._setViewURLs(start)

        self.months = []
        for month in range(1, 13):
            self.months.append(MonthInfo(context.year, month))

        # convert to UTC time offsets
        start = datetime(context.year, 1, 1,
                         0, 0, 0, 0, self.user_timezone).astimezone(UTC)
        end = datetime(context.year+1, 1, 1,
                         0, 0, 0, 0, self.user_timezone).astimezone(UTC)
        for event in context.calendar.expand(start, end):
            dtstart = event.dtstart.astimezone(self.user_timezone)
            self.months[dtstart.month - 1].days[dtstart.day - 1].events.append(event)

        self.daynames = [ d[0] for d in daynames ]
        self.layout = [ [  1,  2,  3 ],
                        [  4,  5,  6 ],
                        [  7,  8,  9 ],
                        [ 10, 11, 12 ] ]


class CalendarEventCollection(object):
    implements(ICalendarEventCollection)

    def __init__(self, calendar):
        self.calendar = calendar

    def __getitem__(self, number):
        return CalendarEvent.get(id=number)



class CalendarEventAddView(AddView):

    __used_for__ = IEditCalendar

    def createAndAdd(self, data):
        """Create a new calendar event.

        `data` is a dictionary with the data entered in the form.
        """
        calendar = self.context
        kw = dict([(str(k), v) for k, v in data.items()])
        event = calendar.addEvent(SimpleCalendarEvent(**kw))
        notify(ObjectCreatedEvent(event))

    def nextURL(self):
        return '.'

class CalendarEventEditView(SQLObjectEditView):
    pass

class ViewCalendarEvent(object):
    __used_for__ = ICalendarEvent
    def __init__(self, context, request):
        self.context = context
        self.request = request
    def __call__(self):
        if checkPermission('launchpad.Edit', self.context):
            self.request.response.redirect('+edit')
        else:
            self.request.response.redirect('+display')

class ViewCalendarSubscriptions(object):
    colours = colours

    def __init__(self, context, request):
        self.context = context
        self.request = request

        person = IPerson(request.principal, None)
        self._subscriptions = CalendarSubscriptionSet(person)

    def subscriptions(self):
        # XXXX should make sure that calendars for person and teams they
        # are a member of are always in the subscription list.
        #  - jamesh 2005-01-25
        for cal in self._subscriptions:
            yield { 'id': cal.id, 'title': cal.title,
                    'subscribed': True,
                    'colour': self._subscriptions.getColour(cal) }

    def submit(self):
        if 'UPDATE_SUBMIT' in self.request.form:
            if self.request.method != "POST":
                raise RuntimeError("This form must be posted!")
            # iterate through calendar ids:
            for id in [ int(name[4:]) for name in self.request.form.keys()
                        if re.match(r'sub.\d+', name) ]:
                try:
                    calendar = Calendar.get(id=id)
                except SQLObjectNotFound:
                    raise RuntimeError("Unknown calendar ID found in submitted form data")
                if self.request.form.get('sub.%d' % id, None) != 'no':
                    self._subscriptions.subscribe(calendar)
                else:
                    self._subscriptions.unsubscribe(calendar)

                colour = self.request.get('colour.%d' % id, None)
                if colour:
                    self._subscriptions.setColour(calendar, colour)

class ViewCalendarSubscribe(object):
    colours = colours

    def __init__(self, context, request):
        self.context = ILaunchpadCalendar(context)
        self.request = request

        person = IPerson(request.principal, None)
        self._subscriptions = CalendarSubscriptionSet(person)

    def subscribed(self):
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
            colour = self.request.get('colour', None)
            if colour:
                self._subscriptions.setColour(self.context, colour)


class CalendarInfoPortletView(object):
    def __init__(self, view):
        self.request = view.request
        self.context = ICalendarOwner(view.context).calendar

        self.user_timezone = getUtility(ILaunchBag).timezone
        now = datetime.now(self.user_timezone)

        self.month ='%s %04d' % (monthnames[now.month-1], now.year)


        # create array of day information for each day of the month
        self.daynames = [ d[0] for d in daynames ]
        self.days = []
        for i in range(calendar.monthrange(now.year, now.month)[1]):
            self.days.append({ 'day': i+1,
                               'dayURL': 'calendar/%04d-%02d-%02d'
                                         % (now.year, now.month, i+1),
                               'hasEvents': False })

        # convert to UTC time offsets
        start = date(now.year, now.month, 1)
        end = next_month(start)
        start = datetime(start.year, start.month, 1,
                         0, 0, 0, 0, self.user_timezone).astimezone(UTC)
        end = datetime(end.year, end.month, 1,
                         0, 0, 0, 0, self.user_timezone).astimezone(UTC)

        for event in self.context.expand(start, end):
            dtstart = event.dtstart.astimezone(self.user_timezone)
            self.days[dtstart.day - 1]['hasEvents'] = True

        # lay out the dayinfo objects in a 2D grid
        self.layout = calendar.monthcalendar(now.year, now.month)

        self.canSubscribe = (IPerson(self.request.principal, None) is not None)

class CalendarInfoPortlet(object):
    def __init__(self, template_filename):
        self.template = ViewPageTemplateFile(template_filename)
    def __call__(self, view, *args, **kw):
        return self.template(CalendarInfoPortletView(view), *args, **kw)
    def __get__(self, instance, type=None):
        return BoundPageTemplate(self, instance)
