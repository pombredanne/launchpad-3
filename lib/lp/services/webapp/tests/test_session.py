# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from testtools import TestCase
from testtools.matchers import Contains

from lp.services.webapp.servers import LaunchpadTestRequest
from lp.services.webapp.session import (
    get_cookie_domain,
    LaunchpadCookieClientIdManager,
    )


class GetCookieDomainTestCase(TestCase):

    def test_base_domain(self):
        # Test that the base Launchpad domain gives a domain parameter
        # that is visible to the virtual hosts.
        self.assertEqual(get_cookie_domain('launchpad.net'), '.launchpad.net')

    def test_vhost_domain(self):
        # Test Launchpad subdomains give the same domain parameter
        self.assertEqual(get_cookie_domain('bugs.launchpad.net'),
                         '.launchpad.net')

    def test_other_domain(self):
        # Other domains do not return a cookie domain.
        self.assertEqual(get_cookie_domain('example.com'), None)

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


class TestLaunchpadCookieClientIdManager(TestCase):

    def test_httponly(self):
        # Authentication cookies are marked as httponly, so JavaScript
        # can't read them directly.
        request = LaunchpadTestRequest()
        LaunchpadCookieClientIdManager().setRequestId(request, 'some-id')
        self.assertThat(
            dict(request.response.getHeaders())['Set-Cookie'],
            Contains('; httponly;'))
