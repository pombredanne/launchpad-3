"""
Calendaring for Launchpad

This package is a prototype of calendaring for launchpad.
"""

import re
import datetime

from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.app import zapi
from zope.publisher.interfaces import IPublishTraverse
from zope.publisher.interfaces import NotFound

from schoolbell.interfaces import ICalendar
from canonical.launchpad.interfaces import IPerson

__metaclass__ = type


class UsersCalendarTraverser:
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
        return ICalendar(person, None)

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


