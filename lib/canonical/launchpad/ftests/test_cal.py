"""
Functional tests for calendars in canonical.launchpad.
"""

import unittest
from zope.testing import doctest
from canonical.functional import FunctionalTestSetup
from canonical.testing import LaunchpadFunctionalLayer

__metaclass__ = type


def doctest_adaptation():
    """Test adapter configuration in canonical/launchpad/zcml/calendar.zcml

    There should be an adapter from ICalendarOwner to ICalendar.

        >>> from canonical.launchpad.interfaces.cal import ICalendarOwner
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

def test_suite():
    suite = doctest.DocTestSuite()
    suite.layer = LaunchpadFunctionalLayer
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
