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


def doctest_MergedCalendarTraverser():
    """Unit test for canonical.calendar.MergedCalendarTraverser

    For the purposes of this test we will need a principal that can be
    adapted to IPerson.

        >>> from canonical.launchpad.interfaces.person import IPerson
        >>> from canonical.launchpad.components.cal import MergedCalendar
        >>> class FakePrincipal:
        ...     def __conform__(self, protocol):
        ...         if protocol is IPerson:
        ...             return FakePerson()

        >>> from schoolbell.interfaces import ICalendar
        >>> class FakePerson:
        ...     displayname = browsername = 'Fake Person'

    MergedCalendarTraverser ignores its context, instead, it gets the
    currently logged on person from the request and creates a
    MergedCalendar object for the user.

        >>> from canonical.launchpad.components.cal import MergedCalendarTraverser
        >>> class AnyContext:
        ...     def __repr__(self):
        ...         return '<AnyContext>'
        >>> context = AnyContext()
        >>> request = TestRequest()
        >>> mct = MergedCalendarTraverser(context, request)

    To do so it implements IBrowserPublisher

        >>> verifyObject(IBrowserPublisher, mct)
        True

    It has a helper method for extracting the calendar from the principal:

        >>> isinstance(mct._calendar(FakePrincipal()), MergedCalendar)
        True

    If there is no user, this helper returns None

        >>> mct._calendar(None)

        >>> class NonadaptablePrincipal:
        ...     pass
        >>> mct._calendar(NonadaptablePrincipal())

    publishTraverse and browserDefault just delegate to the publishTraverse
    and browserDefault of the views that are registered for the calendar.
    If there is no calendar, or no views providing IPublishTraverse or
    IBrowserPublisher, publication fails with a NotFound error.

    No calendar:

        >>> request.setPrincipal(NonadaptablePrincipal())
        >>> mct._calendar(request.principal)

        >>> mct.publishTraverse(request, '2004')
        Traceback (most recent call last):
          ...
        NotFound: Object: <AnyContext>, name: 'calendar'

        >>> mct.browserDefault(request)
        Traceback (most recent call last):
          ...
        NotFound: Object: <AnyContext>, name: 'calendar'

    Calendar exists, but there are no views for it.

        >>> request.setPrincipal(FakePrincipal())
        >>> isinstance(mct._calendar(request.principal), MergedCalendar)
        True

        >>> mct.publishTraverse(request, '2004')
        Traceback (most recent call last):
          ...
        NotFound: Object: <AnyContext>, name: 'calendar'

        >>> mct.browserDefault(request)
        Traceback (most recent call last):
          ...
        NotFound: Object: <AnyContext>, name: 'calendar'

    Calendar exists and there are views.

        >>> from zope.publisher.interfaces import IPublishTraverse
        >>> class FakeCalendarPublishTraverse:
        ...     implements(IPublishTraverse)
        ...     def __init__(self, context, request):
        ...         pass
        ...     def publishTraverse(self, request, name):
        ...         print 'publishTraverse called for %s' % name

        >>> ztapi.browserViewProviding(MergedCalendar,
        ...                            FakeCalendarPublishTraverse,
        ...                            IPublishTraverse)

        >>> mct.publishTraverse(request, '2004')
        publishTraverse called for 2004

        >>> from zope.publisher.interfaces.browser import IBrowserPublisher
        >>> class FakeCalendarBrowserPublisher(FakeCalendarPublishTraverse):
        ...     implements(IBrowserPublisher)
        ...     def browserDefault(self, request):
        ...         print 'browserDefault called'

        >>> ztapi.browserViewProviding(MergedCalendar,
        ...                            FakeCalendarBrowserPublisher,
        ...                            IBrowserPublisher)

        >>> mct.browserDefault(request)
        browserDefault called

    No calendar, and there are views for everything (regression test):

        >>> request.setPrincipal(NonadaptablePrincipal())
        >>> mct._calendar(request.principal)
        >>> ztapi.browserViewProviding(None,
        ...                            FakeCalendarBrowserPublisher,
        ...                            IBrowserPublisher)

        >>> mct.publishTraverse(request, '2004')
        Traceback (most recent call last):
          ...
        NotFound: Object: <AnyContext>, name: 'calendar'

        >>> mct.browserDefault(request)
        Traceback (most recent call last):
          ...
        NotFound: Object: <AnyContext>, name: 'calendar'


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

        >>> from canonical.launchpad.components.cal import CalendarAdapterTraverser
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
