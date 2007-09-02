# Copyright 2005 Canonical Ltd.  All rights reserved.
"""
Test our test harnesses.

A lot of this is duplicated in canonical/launchpad/doc/testing.txt,
but this file is still useful as it runs the tests *twice*, ensuring
that the tearDown methods don't leave things in a mess.
"""
__metaclass__ = type

import unittest
from zope.app import zapi
from harness import LaunchpadTestCase, LaunchpadFunctionalTestCase
from zope.app.mail.interfaces import IMailer

from canonical.launchpad.database.person import Person
from canonical.testing import LaunchpadFunctionalLayer


class TestLaunchpadTestCase(LaunchpadTestCase):
    def test_sampledata(self):
        con = self.connect()
        cur = con.cursor()
        cur.execute("""
            select count(*) from person
            where displayname='Mark Shuttleworth'
            """)
        r = cur.fetchone()
        self.failUnlessEqual(r[0], 1, 'sample data not loaded')
        cur.close()
        con.close()

class TestLaunchpadFunctionalTestCase(LaunchpadFunctionalTestCase):
    layer = LaunchpadFunctionalLayer
    def test_sampledata(self):
        con = self.connect()
        cur = con.cursor()
        cur.execute("""
            select count(*) from person
            where displayname='Mark Shuttleworth'
            """)
        r = cur.fetchone()
        self.failUnlessEqual(r[0], 1, 'sample data not loaded')
        cur.close()
        con.close()

    def test_sqlos(self):
        # Make sure we can access stuff through SQLOS, which complicates
        # the Z3 setup/teardown
        p = Person.get(1)

    def test_placeless(self):
        # Do something that requires functional machinery loaded
        zapi.getUtility(IMailer, 'smtp')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestLaunchpadTestCase))
    suite.addTest(unittest.makeSuite(TestLaunchpadFunctionalTestCase))
    # And again, to make sure all the setup/teardown stuff is working
    suite.addTest(unittest.makeSuite(TestLaunchpadTestCase))
    suite.addTest(unittest.makeSuite(TestLaunchpadFunctionalTestCase))
    return suite

if __name__ == '__main__':
    unittest.main()

