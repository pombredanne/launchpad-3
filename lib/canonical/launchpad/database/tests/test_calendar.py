"""
Unit tests for canonical.launchpad.database.calendar
"""

import unittest
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
        self._objects = {}
        self._next_id = 1

    def ignore(self, *args, **kw):
        pass

    register = ignore # connection._dm.register()
    created = ignore # connection.cache.created()
    get = ignore # connection.cache.get() -- return None
    put = ignore # connection.cache.put()
    finishPut = ignore # connection.cache.finishPut()

    def queryInsertID(self, soInstance, id, names, values):
        id = self._next_id
        self._next_id += 1
        self._objects[id] = dict(zip(names, values))
        return id

    def _SO_selectOne(self, so, columnNames):
        values = self._objects.get(so.id)
        if values is None:
            return []
        return [values[name] for name in columnNames]


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
        >>> from canonical.launchpad.interfaces.calendar \
        ...     import ILaunchpadCalendar
        >>> verifyObject(ILaunchpadCalendar, cal)
        True

    TODO: actually test those methods

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
