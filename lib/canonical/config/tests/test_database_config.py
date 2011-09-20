# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.config import (
    config,
    DatabaseConfig,
    dbconfig,
    )
from canonical.launchpad.readonly import read_only_file_exists
from canonical.launchpad.tests.readonly import (
    remove_read_only_file,
    touch_read_only_file,
    )
from canonical.testing.layers import DatabaseLayer
from lp.testing import TestCase


class TestDatabaseConfig(TestCase):

    layer = DatabaseLayer

    def test_overlay(self):
        # The dbconfig option overlays the database configurations of a
        # chosen config section over the base section.
        self.assertRaises(
            AttributeError, getattr, config.database, 'dbuser')
        self.assertRaises(
            AttributeError, getattr, config.launchpad, 'main_master')
        self.assertEquals('launchpad_main', config.launchpad.dbuser)
        self.assertEquals('librarian', config.librarian.dbuser)

        dbconfig.setConfigSection('librarian')
        expected_db = (
            'dbname=%s host=localhost' % DatabaseLayer._db_fixture.dbname)
        self.assertEquals(expected_db, dbconfig.rw_main_master)
        self.assertEquals('librarian', dbconfig.dbuser)

        dbconfig.setConfigSection('launchpad')
        self.assertEquals(expected_db, dbconfig.rw_main_master)
        self.assertEquals('launchpad_main', dbconfig.dbuser)

    def test_override(self):
        # dbuser and isolation_level can be overridden at runtime, without
        # requiring a custom config overlay.
        dbc = DatabaseConfig()
        dbc.setConfigSection('launchpad')
        self.assertEqual('launchpad_main', dbc.dbuser)
        self.assertEqual('serializable', dbc.isolation_level)

        # dbuser and isolation_level overrides both work.
        dbc.override(dbuser='not_launchpad', isolation_level='autocommit')
        self.assertEqual('not_launchpad', dbc.dbuser)
        self.assertEqual('autocommit', dbc.isolation_level)

        # Overriding dbuser again preserves the isolation_level override.
        dbc.override(dbuser='also_not_launchpad')
        self.assertEqual('also_not_launchpad', dbc.dbuser)
        self.assertEqual('autocommit', dbc.isolation_level)

        # Overriding with None removes the override.
        dbc.override(dbuser=None, isolation_level=None)
        self.assertEqual('launchpad_main', dbc.dbuser)
        self.assertEqual('serializable', dbc.isolation_level)

    def test_required_values(self):
        # Some variables are required to have a value, such as dbuser.  So we
        # get a ValueError if they are not set.
        self.assertRaises(
            AttributeError, getattr, config.codehosting, 'dbuser')
        dbconfig.setConfigSection('codehosting')
        self.assertRaises(ValueError, getattr, dbconfig, 'dbuser')
        dbconfig.setConfigSection('launchpad')

    def test_main_master_and_main_slave(self):
        # DatabaseConfig provides two extra properties: main_master and
        # main_slave, which return the value of either
        # rw_main_master/rw_main_slave or ro_main_master/ro_main_slave,
        # depending on whether or not we're in read-only mode.
        self.assertFalse(read_only_file_exists())
        self.assertEquals(dbconfig.rw_main_master, dbconfig.main_master)
        self.assertEquals(dbconfig.rw_main_slave, dbconfig.main_slave)

        touch_read_only_file()
        try:
            self.assertTrue(read_only_file_exists())
            self.assertEquals(
                dbconfig.ro_main_master, dbconfig.main_master)
            self.assertEquals(
                dbconfig.ro_main_slave, dbconfig.main_slave)
        finally:
            remove_read_only_file()
