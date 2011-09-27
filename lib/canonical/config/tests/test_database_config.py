# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.config import DatabaseConfig
from canonical.launchpad.readonly import read_only_file_exists
from canonical.launchpad.tests.readonly import (
    remove_read_only_file,
    touch_read_only_file,
    )
from canonical.testing.layers import DatabaseLayer
from lp.testing import TestCase


class TestDatabaseConfig(TestCase):

    layer = DatabaseLayer

    def test_override(self):
        # dbuser and isolation_level can be overridden at runtime.
        dbc = DatabaseConfig()
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

    def test_reset(self):
        # reset() removes any overrides.
        dbc = DatabaseConfig()
        self.assertEqual('launchpad_main', dbc.dbuser)
        dbc.override(dbuser='not_launchpad')
        self.assertEqual('not_launchpad', dbc.dbuser)
        dbc.reset()
        self.assertEqual('launchpad_main', dbc.dbuser)

    def test_main_master_and_main_slave(self):
        # DatabaseConfig provides two extra properties: main_master and
        # main_slave, which return the value of either
        # rw_main_master/rw_main_slave or ro_main_master/ro_main_slave,
        # depending on whether or not we're in read-only mode.
        dbc = DatabaseConfig()
        self.assertFalse(read_only_file_exists())
        self.assertEquals(dbc.rw_main_master, dbc.main_master)
        self.assertEquals(dbc.rw_main_slave, dbc.main_slave)

        touch_read_only_file()
        try:
            self.assertTrue(read_only_file_exists())
            self.assertEquals(
                dbc.ro_main_master, dbc.main_master)
            self.assertEquals(
                dbc.ro_main_slave, dbc.main_slave)
        finally:
            remove_read_only_file()
