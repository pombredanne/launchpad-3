# Copyright 2007 Canonical Ltd.  All rights reserved.

import unittest

from canonical.launchpad.webapp.session import get_cookie_domain


class GetCookieDomainTestCase(unittest.TestCase):

    def test_base_domain(self):
        # Test that the base Launchpad domain gives a domain parameter
        # that is visible to the virtual hosts.
        self.assertEqual(get_cookie_domain('launchpad.net'), '.launchpad.net')

    def test_vhost_domain(self):
        # Test Launchpad subdomains give the same domain parameter
        self.assertEqual(get_cookie_domain('bugs.launchpad.net'),
                         '.launchpad.net')

    def test_shipit_domain(self):
        # The shipit domains are outside of the Launchpad tree, so do
        # not return a cookie domain.
        self.assertEqual(get_cookie_domain('shipit.ubuntu.com'), None)
        self.assertEqual(get_cookie_domain('shipit.kubuntu.org'), None)
        self.assertEqual(get_cookie_domain('shipit.edubuntu.org'), None)

    def test_other_instances(self):
        # Test that requests to other launchpad instances are scoped right
        self.assertEqual(get_cookie_domain('demo.launchpad.net'),
                         '.demo.launchpad.net')
        self.assertEqual(get_cookie_domain('bugs.demo.launchpad.net'),
                         '.demo.launchpad.net')

        self.assertEqual(get_cookie_domain('staging.launchpad.net'),
                         '.staging.launchpad.net')
        self.assertEqual(get_cookie_domain('bugs.staging.launchpad.net'),
                         '.staging.launchpad.net')

        self.assertEqual(get_cookie_domain('launchpad.dev'),
                         '.launchpad.dev')
        self.assertEqual(get_cookie_domain('bugs.launchpad.dev'),
                         '.launchpad.dev')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
