#!/usr/bin/env python2.4
##############################################################################
#
# Copyright (c) 2004 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Test script

$Id: test.py 25177 2004-06-02 13:17:31Z jim $
"""
import sys, os, psycopg, time

os.setpgrp() # So test_on_merge.py can reap its children

# Make tests run in a timezone no launchpad developers live in.
# Our tests need to run in any timezone.
# (No longer actually required, as PQM does this)
os.environ['TZ'] = 'Asia/Calcutta'
time.tzset()

here = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(here, 'lib'))

# Set PYTHONPATH environment variable for spawned processes
os.environ['PYTHONPATH'] = ':'.join(sys.path)

# Install the import fascist import hook and atexit handler.
import importfascist
importfascist.install_import_fascist()

# Tell canonical.config to use the test config section in launchpad.conf
from canonical.config import config
config.setDefaultSection('testrunner')

# Turn on psycopg debugging wrapper
#import canonical.database.debug
#canonical.database.debug.install()

# Silence spurious warnings or turn them into errors
import warnings
# Our Z3 is still using whrandom
warnings.filterwarnings(
        "ignore",
        "the whrandom module is deprecated; please use the random module"
        )
# Some stuff got deprecated in 2.4 that we can clean up
warnings.filterwarnings(
        "error", category=DeprecationWarning, module="email"
        )

from canonical.ftests import pgsql
# If this is removed, make sure canonical.ftests.pgsql is updated
# because the test harness there relies on the Connection wrapper being
# installed.
pgsql.installFakeConnect()

# This is a terrible hack to divorce the FunctionalTestSetup from
# its assumptions about the ZODB.
from zope.app.tests.functional import FunctionalTestSetup
FunctionalTestSetup.__init__ = lambda *x: None

# Install our own test runner to to pre/post sanity checks
import zope.app.tests.test
from canonical.database.sqlbase import SQLBase, ZopelessTransactionManager
class LaunchpadTestRunner(zope.app.tests.test.ImmediateTestRunner):
    def precheck(self, test):
        pass

    def postcheck(self, test):
        '''Tests run at the conclusion of every top level test suite'''
        # Confirm Zopeless teardown has been called if necessary
        assert ZopelessTransactionManager._installed is None, \
                'Test used Zopeless but failed to tearDown correctly'

        # Confirm all database connections have been dropped
        assert len(pgsql.PgTestSetup.connections) == 0, \
                'Not all PostgreSQL connections closed'

        # Disabled this check - we now optimize by only dropping the
        # db if necessary
        #
        #con = psycopg.connect('dbname=template1')
        #try:
        #    cur = con.cursor()
        #    cur.execute("""
        #        SELECT count(*) FROM pg_database
        #        WHERE datname='launchpad_ftest'
        #        """)
        #    r = cur.fetchone()[0]
        #    assert r == 0, 'launchpad_ftest database not dropped'
        #finally:
        #    con.close()

    def run(self, test):
        self.precheck(test)
        rv = super(LaunchpadTestRunner, self).run(test)
        self.postcheck(test)
        return rv
zope.app.tests.test.ImmediateTestRunner = LaunchpadTestRunner

if __name__ == '__main__':
    zope.app.tests.test.process_args()
