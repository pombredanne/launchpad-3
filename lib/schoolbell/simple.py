"""
Simple calendar events.
"""

from zope.interface import implements
from schoolbell.interfaces import ICalendarEvent
from schoolbell.mixins import CalendarEventMixin

__metaclass__ = type


class SimpleCalendarEvent(CalendarEventMixin):
    """A simple implementation of ICalendarEvent.

        >>> from datetime import datetime, timedelta
        >>> from zope.interface.verify import verifyObject
        >>> e = SimpleCalendarEvent(datetime(2004, 12, 15, 18, 57),
        ...                         timedelta(minutes=15),
        ...                         'Work on schoolbell.simple')
        >>> verifyObject(ICalendarEvent, e)
        True

    """

    implements(ICalendarEvent)

    def __init__(self, dtstart, duration, title, location=None, unique_id=None,
                 recurrence=None):
        self.dtstart = dtstart
        self.duration = duration
        self.title = title
        self.location = location
        self.unique_id = unique_id
        self.recurrence = recurrence

