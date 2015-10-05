# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os

from fixtures import (
    EnvironmentVariableFixture,
    TestWithFixtures,
    )
import testtools

from lp.services.config import dbconfig
from lp.services.config.fixture import ConfigUseFixture
from lp.testing.layers import BaseLayer
from lp.testing.pgsql import (
    ConnectionWrapper,
    PgTestSetup,
    )


class TestPgTestSetup(testtools.TestCase, TestWithFixtures):

    def assertDBName(self, expected_name, fixture):
        """Check that fixture uses expected_name as its dbname."""
        self.assertEqual(expected_name, fixture.dbname)
        fixture.setUp()
        self.addCleanup(fixture.dropDb)
        self.addCleanup(fixture.tearDown)
        cur = fixture.connect().cursor()
        cur.execute('SELECT current_database()')
        where = cur.fetchone()[0]
        self.assertEqual(expected_name, where)

    def test_db_naming_LP_TEST_INSTANCE_set(self):
        # when LP_TEST_INSTANCE is set, it is used for dynamic db naming.
        BaseLayer.setUp()
        self.addCleanup(BaseLayer.tearDown)
        fixture = PgTestSetup(dbname=PgTestSetup.dynamic)
        expected_name = "%s_%d" % (PgTestSetup.dbname, os.getpid())
        self.assertDBName(expected_name, fixture)

    def test_db_naming_without_LP_TEST_INSTANCE_is_static(self):
        self.useFixture(EnvironmentVariableFixture('LP_TEST_INSTANCE'))
        fixture = PgTestSetup(dbname=PgTestSetup.dynamic)
        expected_name = PgTestSetup.dbname
        self.assertDBName(expected_name, fixture)

    def test_db_naming_stored_in_BaseLayer_configs(self):
        BaseLayer.setUp()
        self.addCleanup(BaseLayer.tearDown)
        fixture = PgTestSetup(dbname=PgTestSetup.dynamic)
        fixture.setUp()
        self.addCleanup(fixture.dropDb)
        self.addCleanup(fixture.tearDown)
        expected_value = 'dbname=%s' % fixture.dbname
        self.assertEqual(expected_value, dbconfig.rw_main_master)
        self.assertEqual(expected_value, dbconfig.rw_main_slave)
        with ConfigUseFixture(BaseLayer.appserver_config_name):
            self.assertEqual(expected_value, dbconfig.rw_main_master)
            self.assertEqual(expected_value, dbconfig.rw_main_slave)


class TestPgTestSetupTuning(testtools.TestCase, TestWithFixtures):

    layer = BaseLayer

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
            # Leave the table.
            ConnectionWrapper.committed = False
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
