"""
Mixins for implementing calendars.
"""


class CalendarMixin:
    """Mixin for implementing ICalendar methods.

    You do not have to use this mixin, however it might make implementation
    easier, albeit potentially slower.

    A class that uses this mixin must already implement ICalendar.__iter__.

        >>> from schoolbell.interfaces import ICalendar
        >>> from zope.interface import implements
        >>> class MyCalendar(CalendarMixin):
        ...     implements(ICalendar)
        ...     def __iter__(self):
        ...         return iter([])
        >>> from zope.interface.verify import verifyObject
        >>> verifyObject(ICalendar, MyCalendar())
        True

    """

    def find(self, unique_id):
        """Find a calendar event with a given UID.

        This particular implementation simply performs a linear search by
        iterating over all events and looking at their UIDs.

            >>> class Event:
            ...     def __init__(self, uid):
            ...         self.unique_id = uid
            >>> cal = CalendarMixin()
            >>> cal.__iter__ = lambda: iter([Event(uid) for uid in 'a', 'b'])

            >>> cal.find('a').unique_id
            'a'
            >>> cal.find('b').unique_id
            'b'
            >>> cal.find('c')
            Traceback (most recent call last):
              ...
            KeyError: 'c'

        """
        for event in self:
            if event.unique_id == unique_id:
                return event
        raise KeyError(unique_id)

    def expand(self, first, last):
        # TODO: write tests and implement this method
        raise NotImplementedError
