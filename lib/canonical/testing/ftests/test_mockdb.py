# Copyright 2007-2008 Canonical Ltd.  All rights reserved.

"""Functional tests for the mockdb module."""

__metaclass__ = type
__all__ = []

import os
import unittest

import psycopg

from canonical.config import config
from canonical.testing import mockdb, DatabaseLayer
from canonical.testing.mockdb import (
        MockDbConnection, RecordCache, ReplayCache, RetryTest, dont_retry,
        )


class MockDbTestCase(unittest.TestCase):
    layer = DatabaseLayer
    cache = None
    connections = None

    def setUp(self):
        """Setup the test environment, defaulting to 'direct' mode."""
        # Turn off automatic use of the infrastructure we need to test
        DatabaseLayer.uninstallMockDb()

        self.test_key = '_mockdb_unittest'
        self.cache_filename = mockdb.cache_filename(self.test_key)
        self.connections = []
        self.recordMode()

    def tearDown(self):
        if os.path.exists(self.cache_filename):
            os.unlink(self.cache_filename)
        self.directMode()

    def closeConnections(self):
        for con in self.connections:
            try:
                con.close()
            except:
                pass
        self.connections = []

    def directMode(self):
        self.closeConnections()
        self.cache = None

    def recordMode(self):
        self.closeConnections()
        self.cache = RecordCache(self.test_key)

    def replayMode(self):
        self.closeConnections()
        self.cache = ReplayCache(self.test_key)

    def modes(self):
        """This generator allows a test to run the same block under
        the three different modes - original, record & replay.
        """
        # Do things three times, first in direct mode using a real
        # database connection...
        self.directMode()
        yield 'direct'

        # Then in mock db mode, recording.
        self.recordMode()
        yield 'record'

        # And finally, after storing the previous run, in replay mode.
        self.cache.store()
        self.replayMode()
        yield 'replay'

    def connect(self):
        """Open a connection to the (possibly fake) database."""
        # Genuine mode.
        if self.cache is None:
            con = DatabaseLayer.connect()

        # Mock modes.
        else:
            if isinstance(self.cache, RecordCache):
                real_connection = DatabaseLayer.connect()
            else:
                real_connection = None
            con = MockDbConnection(self.cache, real_connection)
        self.connections.append(con)
        return con

    @dont_retry
    def testIncorrectReplay(self):
        # Record nothing but a close on a single connection.
        con = self.connect()
        con.close()
        self.cache.store()

        # Replay correctly.
        self.replayMode()
        con = self.connect()
        con.close()

        # Replay incorrectly.
        self.replayMode()
        con = self.connect()
        self.assertRaises(RetryTest, con.rollback)

    @dont_retry
    def testMultipleConnections(self):
        # Ensure that commands issued via different connections
        # maintain their global order.
        con1 = self.connect()
        con2 = self.connect()
        con1.close()
        con2.close()
        self.cache.store()

        # Replay correctly.
        self.replayMode()
        con1 = self.connect()
        con2 = self.connect()
        con1.close()
        con2.close()

        # Replay in the wrong order.
        self.replayMode()
        con1 = self.connect()
        con2 = self.connect()
        self.assertRaises(RetryTest, con2.close)

    @dont_retry
    def testConnectionParams(self):
        # Make sure we can correctly connect with different connection parms.
        for mode in self.modes():
            for dbuser in ['launchpad', 'testadmin']:
                connection_string = "dbname=%s user=%s host=%s" % (
                        config.dbname, dbuser, config.dbhost
                        )

                if mode == 'direct':
                    con = psycopg.connect(connection_string)
                elif mode == 'record':
                    con = MockDbConnection(
                            self.cache, psycopg.connect(connection_string),
                            connection_string
                            )
                else:
                    con = MockDbConnection(
                            self.cache, None, connection_string
                            )

                cur = con.cursor()
                cur.execute("SHOW session authorization")
                self.failUnlessEqual(cur.fetchone()[0], dbuser)

        # Confirm that unexpected connection parameters raises a RetryTest.
        self.replayMode()
        self.assertRaises(
                RetryTest, MockDbConnection, self.cache, None, "whoops"
                )

    @dont_retry
    def testFailedConnection(self):
        # Ensure failed database connection are reproducable.
        for mode in self.modes():
            connection_string = "dbname=not_a_sausage host=%s user=yourmom" % (
                    config.dbhost
                    )
            try:
                if mode == 'direct':
                    con = psycopg.connect(connection_string)
                elif mode == 'record':
                    con = MockDbConnection(
                            self.cache, psycopg.connect(connection_string),
                            connection_string
                            )
                else:
                    con = MockDbConnection(
                            self.cache, None, connection_string
                            )
            except psycopg.OperationalError:
                pass
            else:
                self.fail("Failed to fail to connect.")

    @dont_retry
    def testNoopSession(self):
        # Minimal do-nothing case.
        for mode in self.modes():
            con = self.connect()

    @dont_retry
    def testSimpleQuery(self):
        # Ensure that we can cache and replay a simple query.
        for mode in self.modes():
            con = self.connect()
            cur = con.cursor()

            # Query without parameters.
            cur.execute("SELECT name FROM Person WHERE name='stub'")
            name = cur.fetchone()[0]
            self.assertEqual(name, 'stub')

            # Query with list parameters.
            cur.execute("SELECT name FROM Person WHERE name=%s", ('sabdfl',))
            name = cur.fetchone()[0]
            self.assertEqual(name, 'sabdfl')

            # Query with dictionary parameters.
            cur.execute(
                    "SELECT name FROM Person WHERE name=%(name)s",
                    {'name': 'carlos'}
                    )
            name = cur.fetchone()[0]
            self.assertEqual(name, 'carlos')

    @dont_retry
    def testExceptions(self):
        # Confirm that expected exceptions are raised correctly.
        for mode in self.modes():
            con = self.connect()
            cur = con.cursor()
            self.assertRaises(
                    psycopg.ProgrammingError,
                    cur.execute, "SELECT blood FROM Stone"
                    )

    @dont_retry
    def testUnexpectedQuery(self):
        for mode in self.modes():
            con = self.connect()
            cur = con.cursor()
            if mode != 'replay':
                cur.execute("SELECT name FROM Person WHERE name='sabdfl'")
            else:
                # Issue an unexpected query in replay mode. A RetryTest
                # exception should be raised.
                self.assertRaises(
                        RetryTest, cur.execute,
                        "SELECT name FROM Person WHERE name='stub'"
                        )

    @dont_retry
    def testUnexpectedQueryParameters(self):
        for mode in self.modes():
            con = self.connect()
            cur = con.cursor()
            query = "SELECT name FROM Person WHERE name=%s"
            if mode != 'replay':
                cur.execute(query, ('sabdfl',))
            else:
                # Issue a query with unexpected bound parameters in replay
                # mode. A RetryTest should be raised.
                self.assertRaises(
                        RetryTest, cur.execute,
                        query, ('stub',)
                        )

    @dont_retry
    def testCommit(self):
        # Confirm commit behavior.
        for mode in self.modes():

            con = self.connect()
            cur = con.cursor()

            # Ensure we have a known value.
            cur.execute("SELECT displayname FROM Person WHERE name='stub'")
            self.failUnlessEqual(cur.fetchone()[0], "Stuart Bishop")

            # Change the known value...
            cur.execute(
                    "UPDATE Person SET displayname='Foo' WHERE name='stub'"
                    )

            # Ensure it isn't visible to other connetions...
            con2 = self.connect()
            cur2 = con2.cursor()
            cur2.execute("SELECT displayname FROM Person WHERE name='stub'")
            self.failUnlessEqual(cur2.fetchone()[0], "Stuart Bishop")

            # And commit.
            con.commit()

            # Confirm that the changed value is visible from a
            # fresh connection.
            con = self.connect()
            cur = con.cursor()
            cur.execute("SELECT displayname FROM Person WHERE name='stub'")
            self.failUnlessEqual(
                    cur.fetchone()[0], "Foo",
                    "Commit not seen by subsequent transaction"
                    )

            # Put back the known value for the next loop.
            cur.execute("""
                UPDATE Person SET displayname='Stuart Bishop'
                WHERE name='stub'
                """)
            con.commit()


    @dont_retry
    def testRollback(self):
        # Confirm rollback behavior.
        for mode in self.modes():
            con1 = self.connect()
            cur1 = con1.cursor()

            # Ensure known state
            cur1.execute("SELECT displayname FROM Person WHERE name='stub'")
            self.failUnlessEqual(cur1.fetchone()[0], "Stuart Bishop")

            # Update a row and rollback.
            cur1.execute(
                "UPDATE Person SET displayname='Foo' WHERE name='stub'"
                )
            con1.rollback()

            # Confirm change wasn't committed.
            con2 = self.connect()
            cur2 = con2.cursor()
            cur2.execute("SELECT displayname FROM Person WHERE name='stub'")
            self.failUnlessEqual(
                    cur2.fetchone()[0], "Stuart Bishop",
                    "Rollback did not roll back changes."
                    )

    @dont_retry
    def testClose(self):
        # Confirm and record close behavior.
        for mode in self.modes():
            con = self.connect()
            cur = con.cursor()
            con.close()
            self.assertRaises(
                    psycopg.Error, cur.execute,
                    "SELECT name FROM Person WHERE name='stub'"
                    )
            # Should raise an exception according to the DB-API, but
            # psycopg doesn't do this. Our wrapper works according to the
            # DB-API so we can enforce nice behavior even where psycopg
            # allows bad behavior.
            if mode == 'direct':
                con.close()
            else:
                self.assertRaises(psycopg.Error, con.close)

    @dont_retry
    def testCursorDescription(self):
        # Confirm cursor.description behavior.
        for mode in self.modes():
            con = self.connect()
            cur = con.cursor()
            cur.execute(
                    "UPDATE Person SET displayname='Foo' WHERE name='stub'"
                    )
            self.failUnless(cur.description is None)

            cur.execute("SELECT name FROM Person WHERE name='stub'")
            desc = cur.description
            self.failIf(desc is None, "description should be set")
            self.failUnlessEqual(len(desc), 1) # One column retrieved.
            self.failUnlessEqual(len(desc[0]), 7) # And it must be a 7-tuple.
            self.failUnlessEqual(desc[0][0], "name")
            self.failUnlessEqual(desc[0][1], psycopg.STRING)

            # Make sure our record and replay descriptions are identical to
            # the direct description.
            if mode == 'direct':
                direct_description = cur.description
            else:
                self.failUnlessEqual(direct_description, cur.description)

    @dont_retry
    def testCursorRowcount(self):
        # Confirm and record cursor.rowcount behavior.
        for mode in self.modes():
            con = self.connect()
            cur = con.cursor()
            self.failUnlessEqual(cur.rowcount, -1)

            # Confirm fetchone() behavior.
            cur.execute(
                    "SELECT name FROM Person WHERE name IN ('stub', 'sabdfl')"
                    )
            self.failUnless(cur.rowcount in (-1, 2)) # Ambiguous state.
            cur.fetchone()
            self.failUnless(cur.rowcount in (-1, 2)) # Ambiguous state.
            cur.fetchone()
            self.failUnlessEqual(cur.rowcount, 2)

            # Confirm fetchall() behavior.
            cur.execute("""
                    SELECT name FROM Person
                    WHERE name IN ('stub', 'sabdfl', 'carlos')
                    """)
            cur.fetchall()
            self.failUnlessEqual(cur.rowcount, 3)

            # Confirm no results behavior.
            cur.execute("SELECT name FROM Person WHERE FALSE")
            cur.fetchall()
            self.failUnlessEqual(cur.rowcount, 0)

            # Confirm update behavior.
            cur.execute("SELECT COUNT(*) FROM Person")
            expected_rowcount = cur.fetchone()[0]
            cur.execute("UPDATE Person SET displayname='Fnord'")
            self.failUnlessEqual(cur.rowcount, expected_rowcount)

            # Confirm delete behavior
            cur.execute("DELETE FROM WikiName WHERE person=1")
            self.failUnlessEqual(cur.rowcount, 1)

    @dont_retry
    def testCursorClose(self):
        # Confirm and record cursor.close behavior.
        for mode in self.modes():
            con = self.connect()
            cur = con.cursor()
            cur.close()
            self.failUnlessRaises(
                    psycopg.Error, cur.execute,
                    "SELECT name FROM Person WHERE name='stub'"
                    )
            cur = con.cursor()
            cur.execute("SELECT name FROM Person WHERE name='stub'")

    @dont_retry
    def testFetchOne(self):
        for mode in self.modes():
            con = self.connect()
            cur = con.cursor()
            try:
                row = cur.fetchone()
                # psycopg seems to be indeterminite in this case! Let it pass.
                # Our mock db follows the standard consistently.
                if mode == 'direct' and row is None:
                    pass
                else:
                    self.fail("%r failed in mode %s" % (cur, mode))
            except psycopg.Error:
                pass # No query yet. Correct to raise an exception.
            cur.execute("UPDATE Person SET displayname='Foo' WHERE name='stub'")
            self.assertRaises(psycopg.Error, cur.fetchone) # Not a SELECT
            cur.execute("SELECT 1 FROM generate_series(1, 10)")
            for i in range(0, 10):
                row = cur.fetchone()
                self.failIf(row is None,
                        "Not enough results - only %d rows" % i)
                self.failUnlessEqual(len(row), 1, "Should be a single column")
                self.failUnlessEqual(row[0], 1, "Bad result %s" % repr(row))
            self.failUnless(cur.fetchone() is None, "Too many results")

    @dont_retry
    def testCursorIteration(self):
        # psycopg1 does not support this extension.
        for mode in self.modes():
            con = self.connect()
            cur = con.cursor()
            self.failIf(hasattr(cur, '__iter__'), "Cursor supports __iter__()")
            self.failIf(hasattr(cur, 'next'), "Cursor supports next()")
        ##  con = self.connect()
        ##  cur = con.cursor()
        ##  cur.execute("SELECT 1 FROM generate_series(1, 10)")
        ##  row_count = 0
        ##  for row in cur:
        ##      row_count += 1
        ##      self.failIfEqual(row_count, 11, "Too many results")
        ##      self.failIf(row is None,
        ##          "Not enough results - only %d rows" % row_count)
        ##      self.failUnlessEqual(
        ##          len(row), 1, "Should be a single column"
        ##          )
        ##      self.failUnlessEqual(row[0], 1, "Bad result %s" % repr(row))
  
    @dont_retry
    def testFetchAll(self):
        for mode in self.modes():
            con = self.connect()
            cur = con.cursor()
            if mode != 'direct':
                # We only do this test against our mock db. psycopg1 gives
                # a SystemError if fetchall is called before a query issued!
                self.assertRaises(psycopg.Error, cur.fetchall) # No query yet.
            cur.execute(
                    "UPDATE Person SET displayname='Foo' WHERE name='stub'"
                    )
            self.assertRaises(psycopg.Error, cur.fetchall) # Not a SELECT.
            cur.execute("SELECT 1 FROM generate_series(1, 10)")
            rows = list(cur.fetchall())
            self.failUnlessEqual(len(rows), 10)
            cur.fetchall()

 
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(MockDbTestCase))
    return suite

