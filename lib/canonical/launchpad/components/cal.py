"""
Calendaring for Launchpad

This package is a prototype of calendaring for launchpad.
"""

import re
import datetime

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.app import zapi
from zope.publisher.interfaces import IPublishTraverse
from zope.publisher.interfaces import NotFound

from schoolbell.interfaces import ICalendar
from canonical.launchpad.interfaces import IPerson, ILaunchpadCalendar
from canonical.launchpad.interfaces import ICalendarSubscriptionSet

from canonical.launchpad.database import CalendarSubscription

from schoolbell.mixins import CalendarMixin, EditableCalendarMixin
from schoolbell.icalendar import convert_calendar_to_ical

__metaclass__ = type

class MergedCalendarTraverser:
    """View for finding the calendar of the authenticated user."""

    implements(IBrowserPublisher)

    name = 'calendar'

    def __init__(self, context, request):
        self.context = context

    def _calendar(self, principal):
        """Return the calendar of principal."""
        person = IPerson(principal, None)
        if person is None:
            return None
        return MergedCalendar(person)

    def publishTraverse(self, request, name):
        """See IPublishTraverse."""
        calendar = self._calendar(request.principal)
        if calendar is not None:
            adapter = zapi.queryViewProviding(calendar, IPublishTraverse,
                                              request, self)
            if adapter is not self:
                return adapter.publishTraverse(request, name)
        raise NotFound(self.context, self.name, request)

    def browserDefault(self, request):
        """See IBrowserPublisher."""
        calendar = self._calendar(request.principal)
        if calendar is not None:
            adapter = zapi.queryViewProviding(calendar, IBrowserPublisher,
                                              request, self)
            if adapter is not self:
                return adapter.browserDefault(request)
        raise NotFound(self.context, self.name, request)


class CalendarAdapterTraverser:
    """View for finding the calendar of the context user.

    context must be adaptable to ICalendar.
    """

    implements(IBrowserPublisher)

    name = 'calendar'

    def __init__(self, context, request):
        self.context = context

    def publishTraverse(self, request, name):
        """See IPublishTraverse."""
        calendar = ICalendar(self.context)
        adapter = zapi.queryViewProviding(calendar, IPublishTraverse,
                                          request, self)
        if adapter is not self:
            return adapter.publishTraverse(request, name)
        raise NotFound(self.context, self.name, request)

    def browserDefault(self, request):
        """See IBrowserPublisher."""
        calendar = ICalendar(self.context)
        adapter = zapi.queryViewProviding(calendar, IBrowserPublisher,
                                          request, self)
        if adapter is not self:
            return adapter.browserDefault(request)
        raise NotFound(self.context, self.name, request)


def calendarFromCalendarOwner(calendarowner):
    """Adapt ICalendarOwner to ICalendar."""
    return calendarowner.calendar


############# Merged Calendar #############

class CalendarSubscriptionSet(object):
    implements(ICalendarSubscriptionSet)

    defaultColour = '#9db8d2'

    def __init__(self, person):
        self.owner = person
    def __contains__(self, calendar):
        if calendar.id is None:
            return False
        return bool(CalendarSubscription.selectBy(personID=self.owner.id,
                                                  calendarID=calendar.id))
    def __iter__(self):
        for sub in CalendarSubscription.selectBy(personID=self.owner.id):
            yield sub.calendar
    def subscribe(self, calendar):
        if calendar.id is None:
            raise ValueError('calendar has no identifier')
        if calendar not in self:
            CalendarSubscription(person=self.owner, calendar=calendar)
    def unsubscribe(self, calendar):
        if calendar.id is None:
            raise ValueError('calendar has no identifier')
        for sub in CalendarSubscription.selectBy(personID=self.owner.id,
                                                 calendarID=calendar.id):
            sub.destroySelf()

    def getColour(self, calendar):
        if calendar.id is None:
            return defaultColour
        for sub in CalendarSubscription.selectBy(personID=self.owner.id,
                                                 calendarID=calendar.id):
            return sub.colour
        else:
            return defaultColour
    def setColour(self, calendar, colour):
        if not re.match(r'#[0-9A-Fa-f]{6}', colour):
            raise ValueError('invalid colour value "%s"' % colour)
        if calendar.id is None:
            return
        for sub in CalendarSubscription.selectBy(personID=self.owner.id,
                                                 calendarID=calendar.id):
            sub.colour = colour

class MergedCalendar(CalendarMixin, EditableCalendarMixin):
    implements(ILaunchpadCalendar)

    def __init__(self, person):
        self.id = None
        self.owner = person
        self.person = person
        self.subscriptions = CalendarSubscriptionSet(self.person)
        self.revision = 0
        self.title = _('Merged Calendar for %s') % self.person.displayname

    def __iter__(self):
        for calendar in self.subscriptions:
            for event in calendar:
                yield event

    def expand(self, first, last):
        for calendar in self.subscriptions:
            for event in calendar.expand(first, last):
                yield event

    def addEvent(self, event):
        raise NotImplementedError
    def removeEvent(self, event):
        raise NotImplementedError


############# iCalendar export ###################

def ical_datetime(dt):
    return dt.astimezone(_utc_tz).strftime('%Y%m%dT%H%M%SZ')
    
class ViewICalendar(object):
    """Publish an object implementing the ICalendar interface in
    the iCalendar format.  This allows desktop calendar clients to
    display the events."""
    __used_for__ = ICalendar
    def __init__(self, context, request):
        self.context = context
        self.request = request
    def __call__(self):
        result = convert_calendar_to_ical(self.context)
        result = '\r\n'.join(result)

        self.request.response.setHeader('Content-Type', 'text/calendar')
        self.request.response.setHeader('Content-Length', len(result))

        return result
