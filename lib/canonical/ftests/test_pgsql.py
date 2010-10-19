# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os

import testtools

from canonical.ftests.pgsql import (
    ConnectionWrapper,
    PgTestSetup,
    )


class TestPgTestSetup(testtools.TestCase):

    def test_db_naming(self):
        fixture = PgTestSetup(dbname=PgTestSetup.dynamic)
        expected_name = "%s_%s" % (PgTestSetup.dbname, os.getpid())
        self.assertEqual(expected_name, fixture.dbname)
        fixture.setUp()
        self.addCleanup(fixture.dropDb)
        self.addCleanup(fixture.tearDown)
        cur = fixture.connect().cursor()
        cur.execute('SELECT current_database()')
        where = cur.fetchone()[0]
        self.assertEqual(expected_name, where)

    def testOptimization(self):
        # Test to ensure that the database is destroyed only when necessary

        # Make a change to a database
        fixture = PgTestSetup()
        fixture.setUp()
        try:
            con = fixture.connect()
            cur = con.cursor()
            cur.execute('CREATE TABLE foo (x int)')
            con.commit()
            # Fake it so the harness doesn't know a change has been made
            ConnectionWrapper.committed = False
        finally:
            fixture.tearDown()

        # Now check to ensure that the table we just created is still there if
        # we reuse the fixture.
        fixture.setUp()
        try:
            con = fixture.connect()
            cur = con.cursor()
            # This tests that the table still exists, as well as modifying the
            # db
            cur.execute('INSERT INTO foo VALUES (1)')
            con.commit()
        finally:
            fixture.tearDown()

        # Now ensure that the table is gone - the commit must have been rolled
        # back.
        fixture.setUp()
        try:
            con = fixture.connect()
            cur = con.cursor()
            cur.execute('CREATE TABLE foo (x int)')
            con.commit()
            ConnectionWrapper.committed = False # Leave the table
        finally:
            fixture.tearDown()

        # The database should *always* be recreated if a new template had been
        # chosen.
        PgTestSetup._last_db = ('different-template', fixture.dbname)
        fixture.setUp()
        try:
            con = fixture.connect()
            cur = con.cursor()
            # If this fails, TABLE foo still existed and the DB wasn't rebuilt
            # correctly.
            cur.execute('CREATE TABLE foo (x int)')
            con.commit()
        finally:
            fixture.tearDown()

    def test_sequences(self):
        # Sequences may be affected by connections even if the connection
        # is rolled back. So ensure the database is reset fully, in the
        # cases where we just rollback the changes we also need to reset all
        # the sequences.

        # Setup a table that uses a sequence
        fixture = PgTestSetup()
        fixture.setUp()
        try:
            con = fixture.connect()
            cur = con.cursor()
            cur.execute('CREATE TABLE foo (x serial, y integer)')
            con.commit()
            con.close()
            # Fake it so the harness doesn't know a change has been made
            ConnectionWrapper.committed = False
        finally:
            fixture.tearDown()

        sequence_values = []
        # Insert a row into it and roll back the changes. Each time, we
        # should end up with the same sequence value
        for i in range(3):
            fixture.setUp()
            try:
                con = fixture.connect()
                cur = con.cursor()
                cur.execute('INSERT INTO foo (y) VALUES (1)')
                cur.execute("SELECT currval('foo_x_seq')")
                sequence_values.append(cur.fetchone()[0])
                con.rollback()
                con.close()
            finally:
                fixture.tearDown()

        # Fail if we got a diffent sequence value at some point
        for v in sequence_values:
            self.failUnlessEqual(v, sequence_values[0])

        # Repeat the test, but this time with some data already in the
        # table
        fixture.setUp()
        try:
            con = fixture.connect()
            cur = con.cursor()
            cur.execute('INSERT INTO foo (y) VALUES (1)')
            con.commit()
            con.close()
            # Fake it so the harness doesn't know a change has been made
            ConnectionWrapper.committed = False
        finally:
            fixture.tearDown()

        sequence_values = []
        # Insert a row into it and roll back the changes. Each time, we
        # should end up with the same sequence value
        for i in range(1,3):
            fixture.setUp()
            try:
                con = fixture.connect()
                cur = con.cursor()
                cur.execute('INSERT INTO foo (y) VALUES (1)')
                cur.execute("SELECT currval('foo_x_seq')")
                sequence_values.append(cur.fetchone()[0])
                con.rollback()
                con.close()
            finally:
                fixture.tearDown()

        # Fail if we got a diffent sequence value at some point
        for v in sequence_values:
            self.failUnlessEqual(v, sequence_values[0])
