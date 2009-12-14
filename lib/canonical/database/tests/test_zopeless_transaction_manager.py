# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from textwrap import dedent
import unittest

from zope.component import getUtility

from storm.zope.interfaces import IZStorm

from canonical.config import config
from canonical.database.sqlbase import ZopelessTransactionManager
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.testing import TestCase


class TestZopelessTransactionManager(TestCase):

    def test_initZopeless_connects_to_auth_master_db(self):
        # Some scripts might create EmailAddress and Account entries, so
        # initZopeless has to connect to the auth master db.  This is a
        # bugfix test.  The error that this test detects is that the
        # script used to use the main_master database for the
        # auth_master.  In this test, we make sure that the auth_master
        # and main_master have different values in the config, and then
        # show that they are honored.  Prior to the fix, ``auth_master``
        # would have been changed to the same value as ``main_master``.
        # Now we set up our test data and push it on the config.
        auth_master = "dbname=example_launchpad_auth_does_not_exist"
        overlay = dedent("""
            [database]
            main_master: dbname=launchpad_dev
            auth_master: %s
            """ % (auth_master,))
        config.push('new-db', overlay)
        try:
            main_connection_string, auth_connection_string, dbname, dbhost = (
                ZopelessTransactionManager._get_zopeless_connection_config(
                    None, None))
            self.assertEqual(auth_connection_string, auth_master)
        finally:
            # Clean up the configuration
            config.pop('new-db')


class TestZopelessTransactionManager_reset_store(TestCase):
    layer = LaunchpadZopelessLayer

    def test_reset_stores_only_does_so_on_active_stores(self):
        active_stores = sorted(
            item[0] for item in getUtility(IZStorm).iterstores())
        self.assertEquals(active_stores, ['launchpad-main-master', 'session'])
        ZopelessTransactionManager._reset_stores()
        # If any other stores had been reset, they'd be activated and would
        # then be returned by ZStorm.iterstores().
        new_active_stores = sorted(
            item[0] for item in getUtility(IZStorm).iterstores())
        self.assertEquals(active_stores, new_active_stores)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
