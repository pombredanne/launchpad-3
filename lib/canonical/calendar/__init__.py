"""
Calendaring for Launchpad

This package is a prototype of calendaring for launchpad.
"""

from zope.interface import implements, Interface
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.app import zapi
from zope.publisher.interfaces import IPublishTraverse
from zope.publisher.interfaces import NotFound

from schoolbell.interfaces import ICalendar
from canonical.launchpad.interfaces import ILaunchpadCalendar, ICalendarOwner
from canonical.launchpad.interfaces import IPerson

__metaclass__ = type


class FakeEvent:

    def __init__(self, title):
        self.title = title

class FakeCalendar:
    """Stub for an object providing ICalendar.

    TODO: get rid of this, use a real Calendar class implemented with sqlobject
    """

    implements(ICalendar)

    def __iter__(self):
        return iter([FakeEvent('event 1'), FakeEvent('event 2')])


def fakeCalendarAdapter(person):
    """Fake adapter from anything to ICalendar.

    Currently it is used for IPerson and IPersonApp.

    TODO: get rid of this, use the person.calendar attribute (and
    a different adapter that takes personapp.person.calendar for IPersonApp).
    """
    return FakeCalendar()


class UsersCalendarTraverser:
    """View for finding the calendar of the authenticated user."""

    implements(IBrowserPublisher)

    name = '+calendar'

    def __init__(self, context, request):
        self.context = context

    def _calendar(self, principal):
        """Return the calendar of principal."""
        person = IPerson(principal, None)
        if person is None:
            return None
        return ICalendar(person, None)

    def publishTraverse(self, request, name):
        calendar = self._calendar(request.principal)
        if calendar is not None:
            adapter = zapi.queryViewProviding(calendar, IPublishTraverse,
                                              request, self)
            if adapter is not self:
                return adapter.publishTraverse(request, name)
        raise NotFound(self.context, self.name, request)

    def browserDefault(self, request):
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
        calendar = ICalendar(self.context)
        adapter = zapi.queryViewProviding(calendar, IPublishTraverse,
                                          request, self)
        if adapter is not self:
            return adapter.publishTraverse(request, name)
        raise NotFound(self.context, self.name, request)

    def browserDefault(self, request):
        calendar = ICalendar(self.context)
        adapter = zapi.queryViewProviding(calendar, IBrowserPublisher,
                                          request, self)
        if adapter is not self:
            return adapter.browserDefault(request)
        raise NotFound(self.context, self.name, request)

def calendarFromPersonApp(personapp):
    """Adapt canonical.launchpad.interfaces.IPersonApp to
    canonical.launchpad.interfaces.ICalendar"""
    import sys
    person = personapp.person
    print >> sys.stderr, (personapp, person, person.calendar)
    return person.calendar
