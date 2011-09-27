# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test error views."""

import urllib2

from storm.exceptions import DisconnectionError
from wsgi_intercept import (
    add_wsgi_intercept,
    remove_wsgi_intercept,
    )
from wsgi_intercept.urllib2_intercept import (
    install_opener,
    uninstall_opener,
    )

from canonical.launchpad.webapp.error import (
    DisconnectionErrorView,
    SystemErrorView,
    )
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import (
    LaunchpadFunctionalLayer,
    wsgi_application,
    )
from lp.testing import TestCase
from lp.testing.fixture import PGBouncerFixture

class TestSystemErrorView(TestCase):

    layer = LaunchpadFunctionalLayer

    def test_without_oops_id(self):
        request = LaunchpadTestRequest()
        SystemErrorView(Exception(), request)
        self.assertEquals(500, request.response.getStatus())
        self.assertEquals(
            None,
            request.response.getHeader('X-Lazr-OopsId', literal=True))

    def test_with_oops_id(self):
        request = LaunchpadTestRequest()
        request.oopsid = 'OOPS-1X1'
        SystemErrorView(Exception(), request)
        self.assertEquals(500, request.response.getStatus())
        self.assertEquals(
            'OOPS-1X1',
            request.response.getHeader('X-Lazr-OopsId', literal=True))


class TestDisconnectionErrorView(TestCase):

    layer = LaunchpadFunctionalLayer

    def getHTTPError(self, url):
        try:
            urllib2.urlopen(url)
        except urllib2.HTTPError, error:
            return error
        else:
            self.fail("We should have gotten an HTTP error")            

    def test_error_view_integration(self):
        # Test setup.
        fixture = PGBouncerFixture()
        self.useFixture(fixture)
        # Make urllib2 see our fake in-process appserver.
        add_wsgi_intercept('launchpad.dev', 80, lambda: wsgi_application)
        self.addCleanup(remove_wsgi_intercept, 'launchpad.dev', 80)
        install_opener()
        self.addCleanup(uninstall_opener)
        # Verify things are working initially.
        url = 'http://launchpad.dev/'
        fixture.start()
        urllib2.urlopen(url)
        # Now break the database, and we get an exception, along with our view.
        fixture.stop()
        error = self.getHTTPError(url)
        self.assertEqual(503, error.code)
        # error.msg has body. XXX do something with it.
        
    def test_error_view(self):
        request = LaunchpadTestRequest()
        DisconnectionErrorView(DisconnectionError(), request)
        self.assertEquals(503, request.response.getStatus())
