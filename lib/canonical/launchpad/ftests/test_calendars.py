"""
Functional tests for calendars in canonical.launchpad.

Most of the tests are testing ZCML directives in a very unit-test-like fashion.
They are not unit tests because they need the Zope 3 ZCML machinery to be set
up, so that directives like "adapter" work.  (Oh, and the primary reason I
wrote them was that I was doing test-driven development, and I didn't have any
views at the time, so I couldn't have written page tests. -- Marius Gedminas)
"""

import unittest
from zope.testing import doctest
from canonical.functional import FunctionalTestSetup

__metaclass__ = type


def doctest_adaptation():
    """Test adapter configuration in canonical/launchpad/zcml/calendar.zcml

    There should be an adapter from ICalendarOwner to ICalendar.

        >>> from canonical.launchpad.interfaces.calendar import ICalendarOwner
        >>> from zope.interface import implements
        >>> class FakeCalendarOwner:
        ...     implements(ICalendarOwner)
        ...     calendar = object()
        >>> calendarowner = FakeCalendarOwner()

        >>> from schoolbell.interfaces import ICalendar
        >>> calendar = ICalendar(calendarowner)
        >>> calendar is FakeCalendarOwner.calendar
        True

    """


def doctest_views():
    """Test view configuration in canonical/launchpad/zcml/calendar.zcml

    There should be a view for RootObject, named 'calendar'.

        >>> from zope.app import zapi
        >>> from zope.publisher.browser import TestRequest
        >>> from canonical.publication import rootObject
        >>> request = TestRequest()
        >>> root = rootObject
        >>> view = zapi.getView(root, 'calendar', request)
        >>> from canonical.calendar import UsersCalendarTraverser
        >>> isinstance(view, UsersCalendarTraverser)
        True

    There should be a view for ICalendarOwner, named 'calendar'.

        >>> from zope.interface import implements
        >>> from canonical.launchpad.interfaces.calendar import ICalendarOwner
        >>> class FakeCalendarOwner:
        ...     implements(ICalendarOwner)
        >>> context = FakeCalendarOwner()
        >>> view = zapi.getView(context, 'calendar', request)
        >>> from canonical.calendar import CalendarAdapterTraverser
        >>> isinstance(view, CalendarAdapterTraverser)
        True

    The default view for ICalendar should be '+index'.

        >>> from canonical.calendar import ICalendar
        >>> class FakeCalendar:
        ...     implements(ICalendar)
        >>> context = FakeCalendar()
        >>> zapi.getDefaultViewName(context, request)
        u'+index'

        >>> view = zapi.getView(context, '+index', request)

    """


def setUp(doctest):
    FunctionalTestSetup().setUp()


def tearDown(doctest):
    FunctionalTestSetup().tearDown()


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(setUp=setUp,
                                     tearDown=tearDown)
                ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
