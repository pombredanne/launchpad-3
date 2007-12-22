# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Functional tests for the mockdb module."""

__metaclass__ = type
__all__ = []

import os
import unittest

from canonical.testing import mockdb, DatabaseLayer
from canonical.testing.mockdb import (
        MockDbConnection, RecordCache, ReplayCache, RetryTest,
        )

class MockDbTestCase(unittest.TestCase):
    layer = DatabaseLayer
    cache = None

    def setUp(self):
        self.cache_filename = mockdb.cache_filename('_mockdb_unittest')
        self.recordMode()

    def tearDown(self):
        if os.path.exists(self.cache_filename):
            os.unlink(self.cache_filename)

    def recordMode(self):
        self.cache = RecordCache(self.cache_filename)

    def replayMode(self):
        self.cache = ReplayCache(self.cache_filename)

    def connect(self):
        if isinstance(self.cache, RecordCache):
            real_connection = DatabaseLayer.connect()
        else:
            real_connection = None
        return MockDbConnection(self.cache, real_connection)

    def testNoopSession(self):
        # Record nothing but a close on a single connection
        con = self.connect()
        con.close()
        self.cache.store()

        # Replay correctly
        self.replayMode()
        con = self.connect()
        con.close()

        # Replay incorrectly
        self.replayMode()
        con = self.connect()
        self.assertRaises(RetryTest, con.rollback)

    def testMultipleConnections(self):
        # Ensure that commands issued via different connections need to
        # maintain their global order.
        con1 = self.connect()
        con2 = self.connect()
        con1.close()
        con2.close()
        self.cache.store()

        # Replay correctly
        self.replayMode()
        con1 = self.connect()
        con2 = self.connect()
        con1.close()
        con2.close()

        # Replay in the wrong order
        self.replayMode()
        con1 = self.connect()
        con2 = self.connect()
        self.assertRaises(RetryTest, con2.close)

    def testSimpleQuery(self):
        # Ensure that we can cache and replay a simple query
        con = self.connect()
        cur = con.cursor()

        # Query without parameters
        cur.execute("SELECT name FROM Person WHERE name='stub'")
        name = cur.fetchone()[0]
        self.assertEqual(name, 'stub')

        # Query with list parameters
        cur.execute("SELECT name FROM Person WHERE name=%s", ('sabdfl',))
        name = cur.fetchone()[0]
        self.assertEqual(name, 'sabdfl')

        # Query with dictionary parameters
        cur.execute(
                "SELECT name FROM Person WHERE name=%(name)s",
                {'name': 'carlos'}
                )
        name = cur.fetchone()[0]
        self.assertEqual(name, 'carlos')
        self.cache.store()

        # Now replay
        self.replayMode()
        con = self.connect()
        cur = con.cursor()
        cur.execute("SELECT name FROM Person WHERE name='stub'")
        name = cur.fetchone()[0]
        self.assertEqual(name, 'stub')
        cur.execute("SELECT name FROM Person WHERE name=%s", ('sabdfl',))
        name = cur.fetchone()[0]
        self.assertEqual(name, 'sabdfl')
        cur.execute(
                "SELECT name FROM Person WHERE name=%(name)s",
                {'name': 'carlos'}
                )
        name = cur.fetchone()[0]
        self.assertEqual(name, 'carlos')

        # And replay incorrectly
        self.replayMode()
        con = self.connect()
        cur = con.cursor()
        cur.execute("SELECT name FROM Person WHERE name='stub'")
        name = cur.fetchone()[0]
        self.assertEqual(name, 'stub')
        self.assertRaises(
                RetryTest, cur.execute,
                "SELECT name FROM Person WHERE name=%s", ('carlos',)
                )

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(MockDbTestCase))
    return suite

