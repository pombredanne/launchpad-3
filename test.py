#!/usr/bin/env python2.3
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
import sys, os, psycopg

here = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(here, 'lib'))

# Set PYTHONPATH environment variable for spawned processes
os.environ['PYTHONPATH'] = ':'.join(sys.path)

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
pgsql.installFakeConnect()

# This is a terrible hack to divorce the FunctionalTestSetup from
# its assumptions about the ZODB.
from zope.app.tests.functional import FunctionalTestSetup
FunctionalTestSetup.__init__ = lambda *x: None

# Install our own test runner to to pre/post sanity checks
import zope.app.tests.test
class LaunchpadTestRunner(zope.app.tests.test.ImmediateTestRunner):
    def precheck(self, test):
        pass

    def postcheck(self, test):
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
