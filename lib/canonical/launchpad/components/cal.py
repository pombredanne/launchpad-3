"""
Calendaring for Launchpad

This package is a prototype of calendaring for launchpad.
"""

import datetime

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from zope.interface import implements
from zope.component import getUtility

from schoolbell.interfaces import ICalendar
from canonical.launchpad.interfaces import (
    ILaunchBag, ILaunchpadCalendar, ILaunchpadMergedCalendar,
    ICalendarSubscriptionSet)

from schoolbell.mixins import CalendarMixin, EditableCalendarMixin
from schoolbell.icalendar import convert_calendar_to_ical

__metaclass__ = type


def calendarFromCalendarOwner(calendarowner):
    """Adapt ICalendarOwner to ICalendar."""
    return calendarowner.calendar


############# Merged Calendar #############


class MergedCalendar(CalendarMixin, EditableCalendarMixin):
    implements(ILaunchpadCalendar, ILaunchpadMergedCalendar)

    def __init__(self):
        self.id = None
        self.revision = 0
        self.owner = getUtility(ILaunchBag).user
        self.subscriptions = getUtility(ICalendarSubscriptionSet)
        if self.owner:
            self.title = _('Merged Calendar for %s') % self.owner.browsername
        else:
            self.title = _('Merged Calendar')

    def __iter__(self):
        for calendar in self.subscriptions:
            for event in calendar:
                yield event

    def expand(self, first, last):
        for calendar in self.subscriptions:
            for event in calendar.expand(first, last):
                yield event

    def addEvent(self, event):
        calendar = self.owner.getOrCreateCalendar()
        calendar.addEvent(event)

    def removeEvent(self, event):
        calendar = event.calendar
        calendar.removeEvent(event)


############# iCalendar export ###################

class ViewICalendar:
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
