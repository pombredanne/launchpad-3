"""
Unit tests for canonical.launchpad.database.calendar
"""

import unittest
import datetime
from zope.testing import doctest


class ConnectionStub:
    """Stub for SQLBase._connection.

    This stub is here so that we can write unit tests for objects that
    inherit from canonical.database.sqlbase.SQLBase without actually
    using a database.
    """

    def __init__(self):
        self._dm = self
        self.cache = self
        self._tables = {}  # tables[tableName][numeric_id] == {field: value}
        self._next_id = 1

    def ignore(self, *args, **kw):
        pass

    register = ignore # connection._dm.register()
    created = ignore # connection.cache.created()
    get = ignore # connection.cache.get() -- return None
    put = ignore # connection.cache.put()
    finishPut = ignore # connection.cache.finishPut()

    def queryInsertID(self, soInstance, id, names, values):
        table = self._tables.setdefault(soInstance._table, {})
        if id is None:
            id = self._next_id
            self._next_id += 1
        table[id] = dict(zip(names, values))
        table[id][soInstance._idName] = id
        return id

    def _SO_selectOne(self, so, columnNames):
        table = self._tables.setdefault(so._table, {})
        record = table.get(so.id)
        if record is None:
            return []
        return tuple([record[name] for name in columnNames])

    def _SO_selectOneAlt(self, so, columnNames, column, value):
        table = self._tables.setdefault(so._table, {})
        for record in table.values():
            if record[column] == value:
                return tuple([record[name] for name in columnNames])
        return None

    def _SO_selectJoin(self, soClass, column, value):
        table = self._tables.setdefault(soClass._table, {})
        for record in table.values():
            if record[column] == value:
                yield (record[soClass._idName], )


def setUp(doctest):
    """Install SQLBase._connection stub."""
    from canonical.database.sqlbase import SQLBase
    doctest.old_connection = SQLBase._connection
    SQLBase._connection = ConnectionStub()

def tearDown(doctest):
    """Restore SQLBase._connection."""
    from canonical.database.sqlbase import SQLBase
    SQLBase._connection = doctest.old_connection


def doctest_Calendar():
    r"""Test Calendar.

    A Calendar needs an owner, so we have to create a Person

        >>> from canonical.launchpad.database import Person
        >>> person = Person(name='Joe Developer')

    We can now create a Calendar.

        >>> from canonical.launchpad.database import Calendar
        >>> cal = Calendar(title='Sample calendar', revision=0, owner=person)

        >>> cal.title
        u'Sample calendar'
        >>> cal.revision
        0
        >>> cal.owner.name
        u'Joe Developer'

    Calendars should implement ILaunchpadCalendar (which also inherits from
    ICalendar).

        >>> from zope.interface.verify import verifyObject
        >>> from schoolbell.interfaces import ICalendar
        >>> from canonical.launchpad.interfaces.calendar \
        ...     import ILaunchpadCalendar
        >>> verifyObject(ILaunchpadCalendar, cal)
        True
        >>> verifyObject(ICalendar, cal)
        True

    Calendars are iterable

        >>> list(cal)
        []

    Let us actually create some events so iteration becomes more interesting.

        >>> from canonical.launchpad.database import CalendarEvent
        >>> e1 = CalendarEvent(unique_id="e1", calendar=cal, title="Hack",
        ...                    dtstart=datetime.datetime(2004, 12, 15, 0, 35),
        ...                    duration=datetime.timedelta(minutes=1))
        >>> e2 = CalendarEvent(unique_id="e2", calendar=cal, title="ditto",
        ...                    dtstart=datetime.datetime(2004, 12, 15, 0, 37),
        ...                    duration=datetime.timedelta(minutes=2))

        >>> [e.unique_id for e in cal]
        [u'e1', u'e2']

    You can also look for an event by its unique ID:

        >>> cal.find('e1').title
        u'Hack'
        >>> cal.find('e3')
        Traceback (most recent call last):
          ...
        KeyError: 'e3'

    TODO: test the expand method

    """


def doctest_CalendarEvent():
    r"""Test CalendarEvent.

    A CalendarEvent needs to belong to a Calendar.  A Calendar needs an owner,
    so we have to create a Person.

        >>> from canonical.launchpad.database import Person
        >>> from canonical.launchpad.database import Calendar
        >>> person = Person(name='Joe Developer')
        >>> calendar = Calendar(owner=person, title="Sample calendar")

    We can now create a CalendarEvent

        >>> from canonical.launchpad.database import CalendarEvent
        >>> e1 = CalendarEvent(unique_id="e1", calendar=calendar, title="Hack",
        ...                    dtstart=datetime.datetime(2004, 12, 15, 1, 42),
        ...                    duration=datetime.timedelta(minutes=1))

    Calendar events should implement ICalendarEvent.

        >>> from zope.interface.verify import verifyObject
        >>> from schoolbell.interfaces import ICalendarEvent
        >>> verifyObject(ICalendarEvent, e1)
        True

    TODO: test hasOccurrences and other methods

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
