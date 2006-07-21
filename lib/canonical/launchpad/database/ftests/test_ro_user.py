# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest
import psycopg

from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestCase

class RoUserTestCase(LaunchpadFunctionalTestCase):
    """Test that the RO PostgreSQL user actually has read access"""
    dbuser = 'ro'

    def test(self):
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

def test_suite():
    return unittest.makeSuite(RoUserTestCase)

