# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test error views."""

import urllib2

from storm.exceptions import (
    DisconnectionError,
    OperationalError,
    )
import transaction

from canonical.launchpad.webapp.error import (
    DisconnectionErrorView,
    OperationalErrorView,
    SystemErrorView,
    )
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import (
    LaunchpadFunctionalLayer,
    reconnect_stores,
    )
from lp.testing import TestCase
from lp.testing.fixture import (
    PGBouncerFixture,
    Urllib2Fixture,
    )

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


class TestDatabaseErrorViews(TestCase):

    layer = LaunchpadFunctionalLayer

    def getHTTPError(self, url):
        try:
            urllib2.urlopen(url)
        except urllib2.HTTPError, error:
            return error
        else:
            self.fail("We should have gotten an HTTP error")

    def test_disconnectionerror_view_integration(self):
        # Test setup.
        self.useFixture(Urllib2Fixture())
        bouncer = PGBouncerFixture()
        self.useFixture(bouncer)
        # Verify things are working initially.
        url = 'http://launchpad.dev/'
        urllib2.urlopen(url)
        # Now break the database, and we get an exception, along with our view.
        bouncer.stop()
        # Right now, we do weird hacks in dbpolicy.py.  We can do this instead.
        # for i in range(2):
        #     # This should not happen, but whatever.
        #     self.assertEqual(500,self.getHTTPError(url).code)
        error = self.getHTTPError(url)
        self.assertEqual(503, error.code)
        # error.msg has body. XXX do something with it.
        # We keep seeing the correct exception on subsequent requests.
        self.assertEqual(503, self.getHTTPError(url).code)
        # When the database is available again, requests succeed.
        bouncer.start()
        urllib2.urlopen(url)

    def test_disconnectionerror_view(self):
        request = LaunchpadTestRequest()
        DisconnectionErrorView(DisconnectionError(), request)
        self.assertEquals(503, request.response.getStatus())

    def test_operationalerror_view_integration(self):
        # Test setup.
        self.useFixture(Urllib2Fixture())
        bouncer = PGBouncerFixture()
        self.useFixture(bouncer)
        # This is necessary to avoid confusing PG after the stopped bouncer.
        transaction.abort()
        # Database is down initially, causing an OperationalError.
        bouncer.stop()
        url = 'http://launchpad.dev/'
        error = self.getHTTPError(url)
        self.assertEqual(503, error.code)
        # XXX do something with error.msg.  Distinguish from Disconnection.
        # We keep seeing the correct exception on subsequent requests.
        self.assertEqual(503, self.getHTTPError(url).code)
        # When the database is available again, requests succeed.
        bouncer.start()
        urllib2.urlopen(url)

    def test_operationalerror_view(self):
        request = LaunchpadTestRequest()
        OperationalErrorView(OperationalError(), request)
        self.assertEquals(503, request.response.getStatus())
