# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests confirming that changing isolation levels does what we expect."""

__metaclass__ = type
__all__ = []

import os.path
from subprocess import Popen, PIPE, STDOUT
import sys
from textwrap import dedent
import unittest

from canonical.config import config
from canonical.database.sqlbase import (
    cursor, ISOLATION_LEVEL_AUTOCOMMIT, ISOLATION_LEVEL_DEFAULT,
    ISOLATION_LEVEL_READ_COMMITTED, ISOLATION_LEVEL_SERIALIZABLE,
    connect)
from canonical.testing.layers import LaunchpadZopelessLayer

class TestIsolation(unittest.TestCase):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.txn = LaunchpadZopelessLayer.txn

    def getCurrentIsolation(self, con=None):
        if con is None:
            cur = cursor()
        else:
            cur = con.cursor()
        cur.execute("SELECT * FROM Person")
        cur.execute("SHOW transaction_isolation")
        return cur.fetchone()[0]

    def test_default(self):
        self.failUnlessEqual(self.getCurrentIsolation(), 'read committed')

    def test_default2(self):
        self.txn.set_isolation_level(ISOLATION_LEVEL_DEFAULT)
        self.failUnlessEqual(self.getCurrentIsolation(), 'read committed')

    def test_autocommit(self):
        self.txn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        # There is no actual 'autocommit' mode in PostgreSQL. psycopg
        # implements this feature by using read committed isolation and
        # issuing commit() statements after every query.
        self.failUnlessEqual(self.getCurrentIsolation(), 'read committed')

        # So we need to confirm we are actually in autocommit mode
        # by seeing if we an roll back
        con = self.txn.conn()
        cur = con.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM Person WHERE homepage_content IS NULL")
        self.failIfEqual(cur.fetchone()[0], 0)
        cur.execute("UPDATE Person SET homepage_content=NULL")
        con.rollback()
        cur = con.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM Person WHERE homepage_content IS NOT NULL")
        self.failUnlessEqual(cur.fetchone()[0], 0)

    def test_readCommitted(self):
        self.txn.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
        self.failUnlessEqual(self.getCurrentIsolation(), 'read committed')

    def test_serializable(self):
        self.txn.set_isolation_level(ISOLATION_LEVEL_SERIALIZABLE)
        self.failUnlessEqual(self.getCurrentIsolation(), 'serializable')

    def test_commit(self):
        # Change the isolation level
        self.failUnlessEqual(self.getCurrentIsolation(), 'read committed')
        self.txn.set_isolation_level(ISOLATION_LEVEL_SERIALIZABLE)
        self.failUnlessEqual(self.getCurrentIsolation(), 'serializable')

        con = self.txn.conn()
        cur = con.cursor()
        cur.execute("UPDATE Person SET homepage_content=NULL")
        con.commit()
        cur.execute("UPDATE Person SET homepage_content='foo'")
        self.failUnlessEqual(self.getCurrentIsolation(), 'serializable')

    def test_rollback(self):
        # Change the isolation level
        self.failUnlessEqual(self.getCurrentIsolation(), 'read committed')
        self.txn.set_isolation_level(ISOLATION_LEVEL_SERIALIZABLE)
        self.failUnlessEqual(self.getCurrentIsolation(), 'serializable')

        con = self.txn.conn()
        cur = con.cursor()
        cur.execute("UPDATE Person SET homepage_content=NULL")
        con.rollback()
        self.failUnlessEqual(self.getCurrentIsolation(), 'serializable')

    def test_script(self):
        # Ensure that things work in stand alone scripts too, in case out
        # test infrustructure is faking something.
        script = os.path.join(
                os.path.dirname(__file__), 'script_isolation.py')
        cmd = [sys.executable, script]
        process = Popen(cmd, stdout=PIPE, stderr=STDOUT, stdin=PIPE)
        (script_output, _empty) = process.communicate()
        self.failUnlessEqual(process.returncode, 0, 'Error: ' + script_output)
        self.failUnlessEqual(script_output, dedent("""\
                read committed
                read committed
                serializable
                serializable
                serializable
                serializable
                """))

    def test_connect(self):
        # Ensure connect() method returns a connection with the correct
        # default isolation
        con = connect(config.launchpad.dbuser)
        self.failUnlessEqual(self.getCurrentIsolation(con), 'read committed')
        con.rollback()
        self.failUnlessEqual(self.getCurrentIsolation(con), 'read committed')

        # Ensure that changing the isolation sticks.
        con = connect(
            config.launchpad.dbuser, isolation=ISOLATION_LEVEL_SERIALIZABLE)
        self.failUnlessEqual(self.getCurrentIsolation(con), 'serializable')
        con.rollback()
        self.failUnlessEqual(self.getCurrentIsolation(con), 'serializable')

        # But on a fresh connection, it works just fine.
        con = connect(config.launchpad.dbuser)
        con.set_isolation_level(ISOLATION_LEVEL_SERIALIZABLE)
        self.failUnlessEqual(self.getCurrentIsolation(con), 'serializable')
        con.rollback()
        self.failUnlessEqual(self.getCurrentIsolation(con), 'serializable')
