# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Functional tests for request_country"""
__metaclass__ = type

import unittest
from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestSetup
from canonical.launchpad.ftests import login, ANONYMOUS

from canonical.launchpad.components.request_country import request_country

class RequestCountryTestCase(unittest.TestCase):
    """request_country needs functional tests because it accesses GeoIP
    using a Utility
    """
    lp = '82.211.81.179'

    def setUp(self):
        LaunchpadFunctionalTestSetup().setUp()
        login(ANONYMOUS)

    def tearDown(self):
        LaunchpadFunctionalTestSetup().tearDown()

    def testRemoteAddr(self):
        country = request_country({'REMOTE_ADDR': self.lp})
        self.failUnlessEqual(country.name, u'United Kingdom')

    def testXForwardedFor(self):
        country = request_country({
                'HTTP_X_FORWARDED_FOR': self.lp,
                'REMOTE_ADDR': '1.2.3.4',
                })
        self.failUnlessEqual(country.name, u'United Kingdom')

    def testNestedProxies(self):
        country = request_country({
                'HTTP_X_FORWARDED_FOR':
                    'localhost, 127.0.0.1, %s, 1,1,1,1' % self.lp,
                })
        self.failUnlessEqual(country.name, u'United Kingdom')

    def testMissingHeaders(self):
        country = request_country({})
        self.failUnless(country is None)

    def testIgnoreLocalhost(self):
        country = request_country({'HTTP_X_FORWARDED_FOR': '127.0.0.1'})
        self.failUnless(country is None)

        country = request_country({'REMOTE_ADDR': '127.0.0.1'})
        self.failUnless(country is None)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(RequestCountryTestCase))
    return suite

