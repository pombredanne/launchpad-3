# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests confirming that changing isolation levels does what we expect."""

__metaclass__ = type
__all__ = []

import os.path
from subprocess import (
    PIPE,
    Popen,
    STDOUT,
    )
import sys
from textwrap import dedent
import unittest

import transaction

from lp.services.config import dbconfig
from lp.services.database.sqlbase import (
    connect,
    cursor,
    ISOLATION_LEVEL_SERIALIZABLE,
    )
from lp.testing.layers import (
    disconnect_stores,
    LaunchpadZopelessLayer,
    )


def set_isolation_level(isolation):
    dbconfig.override(isolation_level=isolation)
    disconnect_stores()


class TestIsolation(unittest.TestCase):
    layer = LaunchpadZopelessLayer

    def getCurrentIsolation(self, con=None):
        if con is None:
            cur = cursor()
        else:
            cur = con.cursor()
        cur.execute("SELECT * FROM Person")
        cur.execute("SHOW transaction_isolation")
        return cur.fetchone()[0]

    def test_default(self):
        self.assertEqual(self.getCurrentIsolation(), 'read committed')

    def test_autocommit(self):
        set_isolation_level('autocommit')
        # There is no actual 'autocommit' mode in PostgreSQL. psycopg
        # implements this feature by using read committed isolation and
        # issuing commit() statements after every query.
        self.assertEqual(self.getCurrentIsolation(), 'read committed')

        # So we need to confirm we are actually in autocommit mode
        # by seeing if we an roll back
        cur = cursor()
        cur.execute(
            "SELECT COUNT(*) FROM Person WHERE homepage_content IS NULL")
        self.assertNotEqual(cur.fetchone()[0], 0)
        cur.execute("UPDATE Person SET homepage_content=NULL")
        transaction.abort()
        cur = cursor()
        cur.execute(
            "SELECT COUNT(*) FROM Person WHERE homepage_content IS NOT NULL")
        self.assertEqual(cur.fetchone()[0], 0)

    def test_readCommitted(self):
        set_isolation_level('read_committed')
        self.assertEqual(self.getCurrentIsolation(), 'read committed')

    def test_repeatableRead(self):
        set_isolation_level('repeatable_read')
        self.assertEqual(self.getCurrentIsolation(), 'repeatable read')

    def test_serializable(self):
        set_isolation_level('serializable')
        self.assertEqual(self.getCurrentIsolation(), 'serializable')

    def test_commit(self):
        # Change the isolation level
        self.assertEqual(self.getCurrentIsolation(), 'read committed')
        set_isolation_level('serializable')
        self.assertEqual(self.getCurrentIsolation(), 'serializable')

        cur = cursor()
        cur.execute("UPDATE Person SET homepage_content=NULL")
        transaction.commit()
        cur.execute("UPDATE Person SET homepage_content='foo'")
        self.assertEqual(self.getCurrentIsolation(), 'serializable')

    def test_rollback(self):
        # Change the isolation level
        self.assertEqual(self.getCurrentIsolation(), 'read committed')
        set_isolation_level('serializable')
        self.assertEqual(self.getCurrentIsolation(), 'serializable')

        cur = cursor()
        cur.execute("UPDATE Person SET homepage_content=NULL")
        transaction.abort()
        self.assertEqual(self.getCurrentIsolation(), 'serializable')

    def test_script(self):
        # Ensure that things work in stand alone scripts too, in case out
        # test infrustructure is faking something.
        script = os.path.join(
                os.path.dirname(__file__), 'script_isolation.py')
        cmd = [sys.executable, script]
        process = Popen(cmd, stdout=PIPE, stderr=STDOUT, stdin=PIPE)
        (script_output, _empty) = process.communicate()
        self.assertEqual(process.returncode, 0, 'Error: ' + script_output)
        self.assertEqual(script_output, dedent("""\
                read committed
                read committed
                repeatable read
                repeatable read
                """))

    def test_connect(self):
        # Ensure connect() method returns a connection with the correct
        # default isolation
        con = connect()
        self.assertEqual(self.getCurrentIsolation(con), 'read committed')
        con.rollback()
        self.assertEqual(self.getCurrentIsolation(con), 'read committed')

        # Ensure that changing the isolation sticks.
        con = connect(isolation=ISOLATION_LEVEL_SERIALIZABLE)
        self.assertEqual(self.getCurrentIsolation(con), 'serializable')
        con.rollback()
        self.assertEqual(self.getCurrentIsolation(con), 'serializable')

        # But on a fresh connection, it works just fine.
        con = connect()
        con.set_isolation_level(ISOLATION_LEVEL_SERIALIZABLE)
        self.assertEqual(self.getCurrentIsolation(con), 'serializable')
        con.rollback()
        self.assertEqual(self.getCurrentIsolation(con), 'serializable')
