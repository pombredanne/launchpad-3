# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from textwrap import dedent
import unittest

import psycopg2

from canonical.config import config
from canonical.database.sqlbase import ZopelessTransactionManager
from canonical.launchpad.scripts import execute_zcml_for_scripts
from lp.testing import TestCase


class TestZopelessTransactionManager(TestCase):

    def test_initZopeless_connects_to_auth_master_db(self):
        # Some scripts might create EmailAddress and Account entries, so
        # initZopeless has to connect to the auth master db.
        overlay = dedent("""
            [database]
            main_master: dbname=launchpad_dev 
            auth_master: dbname=launchpad_auth_does_not_exist
            """)
        config.push('new-db', overlay)
        execute_zcml_for_scripts()
        try:
            ZopelessTransactionManager.initZopeless(dbuser='launchpad')
        except psycopg2.OperationalError, e:
            self.assertIn(
                '"launchpad_auth_does_not_exist" does not exist', str(e))
        else:
            self.fail("initZopeless did not connect to the auth master db")
        config.pop('new-db')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
