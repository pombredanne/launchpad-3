# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Test pgsession.py."""

__metaclass__ = type

import unittest
from datetime import timedelta
from zope.component import getUtility
from zope.app.session.interfaces import ISessionDataContainer, ISessionData

from canonical.launchpad.webapp.pgsession import (
        PGSessionDataContainer, PGSessionData
        )
from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestCase

class TestPgSession(LaunchpadFunctionalTestCase):
    dbuser = 'session'
    def setUp(self):
        LaunchpadFunctionalTestCase.setUp(self)

        self.sdc = PGSessionDataContainer()
        
        # Grant permissions on the session tables. In the production
        # environment, the session database and the main launchpad database
        # are seperate, but for the purposes of the test suite they are
        # combined to minimize database setup overheads.
        #cursor = self.sdc.cursor
        #cursor.execute("GRANT ALL ON SessionData TO session")
        #cursor.execute("GRANT ALL ON SessionPkgData TO session")

    def tearDown(self):
        del self.sdc
        LaunchpadFunctionalTestCase.tearDown(self)

    def test_sdc_basics(self):
        # Make sure we have the correct class and it provides the required
        # interface.
        self.failUnless(isinstance(self.sdc, PGSessionDataContainer))
        self.failUnless(ISessionDataContainer.providedBy(self.sdc))

        client_id = 'Client Id'

        # __getitem__ raises a keyerror for an unknown client id
        self.assertRaises(KeyError, self.sdc.__getitem__, client_id)

        # __setitem__ creates a new row in the SessionData table. The
        # passed in value is ignored.
        self.sdc[client_id] = 'ignored'

        # Once __setitem__ is called, we can access the SessionData
        session_data = self.sdc[client_id]
        self.failUnless(isinstance(session_data, PGSessionData))
        self.failUnless(ISessionData.providedBy(session_data))

    def test_sweep(self):
        product_id = 'Product Id'
        client_id1 = 'Client Id #1'
        client_id2 = 'Client Id #2'

        # Create a session
        self.sdc[client_id1] = 'whatever'
        self.sdc[client_id2] = 'whatever'
        
        # Store some session data to ensure we can clean up sessions
        # with data.
        spd = self.sdc[client_id1][product_id]
        spd['key'] = 'value'

        cursor = self.sdc.cursor

        # Do a quick sanity check
        cursor.execute("SELECT client_id FROM SessionData ORDER BY client_id")
        client_ids = [row[0] for row in cursor.fetchall()]
        self.failUnlessEqual(client_ids, [client_id1, client_id2])
        cursor.execute("SELECT COUNT(*) FROM SessionPkgData")
        self.failUnlessEqual(cursor.fetchone()[0], 1)
        
        # Push the session into the past. There is fuzzyness involved
        # in when the sweeping actually happens (to minimize concurrency
        # issues), so we just push it into the far past for testing.
        cursor.execute("""
            UPDATE SessionData
            SET last_accessed = last_accessed - '1 year'::interval
            WHERE client_id = %(client_id1)s
            """, vars())

        # Make the SessionDataContainer think it hasn't swept in a while
        self.sdc._last_sweep = self.sdc._last_sweep - timedelta(days=365)

        # Sweep happens automatically in __getitem__
        self.sdc[client_id2][product_id]

        # So the client_id1 session should now have been removed.
        cursor = self.sdc.cursor
        cursor.execute("SELECT client_id FROM SessionData ORDER BY client_id")
        client_ids = [row[0] for row in cursor.fetchall()]
        self.failUnlessEqual(client_ids, [client_id2])

        # __getitem__ does not cause a sweep though if  sweep has been
        # done recently, to minimize database queries.
        cursor.execute("""
            UPDATE SessionData
            SET last_accessed = last_accessed - '1 year'::interval
            """)
        self.sdc[client_id1] = 'whatever'
        cursor.execute("SeLECT COUNT(*) FROM SessionData")
        self.failUnlessEqual(cursor.fetchone()[0], 2)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPgSession))
    return suite

