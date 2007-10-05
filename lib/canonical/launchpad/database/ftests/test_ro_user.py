# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Tests for read-only users."""

__metaclass__ = type

import unittest
import psycopg

from canonical.launchpad.ftests.harness import (
    LaunchpadTestSetup, LaunchpadFunctionalTestCase)


class RoUserTestCase(LaunchpadFunctionalTestCase):
    """Test that the read-only PostgreSQL user actually has read access"""
    # XXX sinzui 2007-07-12 bug=125569
    # This test should subclass unittest.TestCase. Some reworking
    # is required to migrate this test.
    dbuser = 'ro'

    def test(self):
        """Test that read-only users cannot make changes to the database."""
        # Only one uncancelled, possibly approved unshipped order
        # per user.
        con = self.connect()
        cur = con.cursor()

        # SELECTs should pass
        cur.execute("SELECT * FROM Person")

        # Except on sequences
        cur.execute("SAVEPOINT attempt")
        self.failUnlessRaises(
                psycopg.Error, cur.execute, "SELECT nextval('person_id_seq')"
                )
        cur.execute("ROLLBACK TO SAVEPOINT attempt")

        # UPDATES should fail
        cur.execute("SAVEPOINT attempt")
        self.failUnlessRaises(
                psycopg.Error, cur.execute, "UPDATE Person SET password=NULL"
                )
        cur.execute("ROLLBACK TO SAVEPOINT attempt")

        # DELETES should fail.
        # We need to use a table with no FK references to it
        cur.execute("SAVEPOINT attempt")
        self.failUnlessRaises(
                psycopg.Error, cur.execute, "DELETE FROM WikiName"
                )
        cur.execute("ROLLBACK TO SAVEPOINT attempt")

    def tearDown(self):
        """Tear down this test and recycle the database."""
        # XXX sinzui 2007-07-12 bug=125569
        # Use the DatabaseLayer mechanism to tear this test down.
        LaunchpadTestSetup().force_dirty_database()
        LaunchpadFunctionalTestCase.tearDown(self)


def test_suite():
    """Create the test suite."""
    return unittest.makeSuite(RoUserTestCase)

