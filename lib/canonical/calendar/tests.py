"""
Unit tests for canonical.calendar
"""

import unittest
from zope.testing import doctest
from zope.interface import implements
from zope.interface.verify import verifyObject
from zope.publisher.browser import TestRequest
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.app.tests import placelesssetup, ztapi

__metaclass__ = type


def doctest_UsersCalendarTraverser():
    """Unit test for canonical.calendar.UsersCalendarTraverser

    For the purposes of this test we will need a principal that can be
    adapted to IPerson, and a person that can be adapted to ICalendar.

        >>> from canonical.launchpad.interfaces.person import IPerson
        >>> class FakePrincipal:
        ...     def __conform__(self, protocol):
        ...         if protocol is IPerson:
        ...             return FakePerson()

        >>> from schoolbell.interfaces import ICalendar
        >>> class FakePerson:
        ...     def __conform__(self, protocol):
        ...         if protocol is ICalendar:
        ...             return FakeCalendar()

        >>> class FakeCalendar:
        ...     implements(ICalendar)
        ...     def __repr__(self):
        ...         return '<FakeCalendar>'

    UsersCalendarTraverser ignores its context, instead, it gets the currently
    logged on person from the request and looks up the person's calendar.

        >>> from canonical.calendar import UsersCalendarTraverser
        >>> class AnyContext:
        ...     def __repr__(self):
        ...         return '<AnyContext>'
        >>> context = AnyContext()
        >>> request = TestRequest()
        >>> uct = UsersCalendarTraverser(context, request)

    To do so it implements IBrowserPublisher

        >>> verifyObject(IBrowserPublisher, uct)
        True

    It has a helper method for extracting the calendar from the principal:

        >>> uct._calendar(FakePrincipal())
        <FakeCalendar>

    If there is no user, or if the user cannot be adapted to a calendar, this
    helper returns None

        >>> uct._calendar(None)

        >>> class NonadaptablePrincipal:
        ...     pass
        >>> uct._calendar(NonadaptablePrincipal())

        >>> class NonadaptablePerson:
        ...     pass
        >>> class AdaptablePrincipal:
        ...     def __conform__(self, protocol):
        ...         if protocol is IPerson:
        ...             return NonadaptablePerson()
        >>> uct._calendar(AdaptablePrincipal())

    publishTraverse and browserDefault just delegate to the publishTraverse
    and browserDefault of the views that are registered for the calendar.
    If there is no calendar, or no views providing IPublishTraverse or
    IBrowserPublisher, publication fails with a NotFound error.

    No calendar:

        >>> request.setPrincipal(NonadaptablePrincipal())
        >>> uct._calendar(request.principal)

        >>> uct.publishTraverse(request, '2004')
        Traceback (most recent call last):
          ...
        NotFound: Object: <AnyContext>, name: '+calendar'

        >>> uct.browserDefault(request)
        Traceback (most recent call last):
          ...
        NotFound: Object: <AnyContext>, name: '+calendar'

    Calendar exists, but there are no views for it.

        >>> request.setPrincipal(FakePrincipal())
        >>> uct._calendar(request.principal)
        <FakeCalendar>

        >>> uct.publishTraverse(request, '2004')
        Traceback (most recent call last):
          ...
        NotFound: Object: <AnyContext>, name: '+calendar'

        >>> uct.browserDefault(request)
        Traceback (most recent call last):
          ...
        NotFound: Object: <AnyContext>, name: '+calendar'

    Calendar exists and there are views.

        >>> from zope.publisher.interfaces import IPublishTraverse
        >>> class FakeCalendarPublishTraverse:
        ...     implements(IPublishTraverse)
        ...     def __init__(self, context, request):
        ...         pass
        ...     def publishTraverse(self, request, name):
        ...         print 'publishTraverse called for %s' % name

        >>> ztapi.browserViewProviding(FakeCalendar,
        ...                            FakeCalendarPublishTraverse,
        ...                            IPublishTraverse)

        >>> uct.publishTraverse(request, '2004')
        publishTraverse called for 2004

        >>> from zope.publisher.interfaces.browser import IBrowserPublisher
        >>> class FakeCalendarBrowserPublisher(FakeCalendarPublishTraverse):
        ...     implements(IBrowserPublisher)
        ...     def browserDefault(self, request):
        ...         print 'browserDefault called'

        >>> ztapi.browserViewProviding(FakeCalendar,
        ...                            FakeCalendarBrowserPublisher,
        ...                            IBrowserPublisher)

        >>> uct.browserDefault(request)
        browserDefault called

    No calendar, and there are views for everything (regression test):

        >>> request.setPrincipal(NonadaptablePrincipal())
        >>> uct._calendar(request.principal)
        >>> ztapi.browserViewProviding(None,
        ...                            FakeCalendarBrowserPublisher,
        ...                            IBrowserPublisher)

        >>> uct.publishTraverse(request, '2004')
        Traceback (most recent call last):
          ...
        NotFound: Object: <AnyContext>, name: '+calendar'

        >>> uct.browserDefault(request)
        Traceback (most recent call last):
          ...
        NotFound: Object: <AnyContext>, name: '+calendar'


    """


def doctest_CalendarAdapterTraverser():
    """Unit test for canonical.calendar.CalendarAdapterTraverser

    For the purposes of this test we will need an object (any object)
    that can be adapted to ICalendar.

        >>> from schoolbell.interfaces import ICalendar
        >>> class SomethingWithCalendar:
        ...     def __conform__(self, protocol):
        ...         if protocol is ICalendar:
        ...             return FakeCalendar()
        ...     def __repr__(self):
        ...         return '<SomethingWithCalendar>'

        >>> class FakeCalendar:
        ...     implements(ICalendar)
        ...     def __repr__(self):
        ...         return '<FakeCalendar>'

    CalendarAdapterTraverser adapts its context to ICalendar and then looks
    up the appropriate calendar view.

        >>> from canonical.calendar import CalendarAdapterTraverser
        >>> context = SomethingWithCalendar()
        >>> request = TestRequest()
        >>> cat = CalendarAdapterTraverser(context, request)

    To do so it implements IBrowserPublisher

        >>> verifyObject(IBrowserPublisher, cat)
        True

    publishTraverse and browserDefault just delegate to the publishTraverse
    and browserDefault of the views that are registered for the calendar.
    If there are no views providing IPublishTraverse or IBrowserPublisher,
    publication fails with a NotFound error.

        >>> cat.publishTraverse(request, '2004')
        Traceback (most recent call last):
          ...
        NotFound: Object: <SomethingWithCalendar>, name: '+calendar'

        >>> cat.browserDefault(request)
        Traceback (most recent call last):
          ...
        NotFound: Object: <SomethingWithCalendar>, name: '+calendar'

        >>> from zope.publisher.interfaces import IPublishTraverse
        >>> class FakeCalendarPublishTraverse:
        ...     implements(IPublishTraverse)
        ...     def __init__(self, context, request):
        ...         pass
        ...     def publishTraverse(self, request, name):
        ...         print 'publishTraverse called for %s' % name

        >>> ztapi.browserViewProviding(FakeCalendar,
        ...                            FakeCalendarPublishTraverse,
        ...                            IPublishTraverse)

        >>> cat.publishTraverse(request, '2004')
        publishTraverse called for 2004

        >>> from zope.publisher.interfaces.browser import IBrowserPublisher
        >>> class FakeCalendarBrowserPublisher(FakeCalendarPublishTraverse):
        ...     implements(IBrowserPublisher)
        ...     def browserDefault(self, request):
        ...         print 'browserDefault called'

        >>> ztapi.browserViewProviding(FakeCalendar,
        ...                            FakeCalendarBrowserPublisher,
        ...                            IBrowserPublisher)

        >>> cat.browserDefault(request)
        browserDefault called

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=placelesssetup.setUp,
                                       tearDown=placelesssetup.tearDown))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
