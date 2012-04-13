# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test error views."""


import httplib
from storm.exceptions import (
    DisconnectionError,
    OperationalError,
    )
import time
import transaction
import urllib2

from lp.services.webapp.error import (
    DisconnectionErrorView,
    OperationalErrorView,
    SystemErrorView,
    )
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.testing import TestCase
from lp.testing.fixture import (
    PGBouncerFixture,
    Urllib2Fixture,
    )
from lp.testing.layers import LaunchpadFunctionalLayer
from lp.testing.matchers import Contains


class TimeoutException(Exception):
    pass


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
        # Now break the database, and we get an exception, along with
        # our view.
        bouncer.stop()
        for i in range(2):
            # This should not happen ideally, but Stuart is OK with it
            # for now.  His explanation is that the first request
            # makes the PG recognize that the slave DB is
            # disconnected, the second one makes PG recognize that the
            # master DB is disconnected, and third and subsequent
            # requests, as seen below, correctly generate a
            # DisconnectionError.  Oddly, these are ProgrammingErrors.
            self.getHTTPError(url)
        error = self.getHTTPError(url)
        self.assertEqual(503, error.code)
        self.assertThat(error.read(),
                        Contains(DisconnectionErrorView.reason))
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
        self.assertThat(error.read(),
                        Contains(OperationalErrorView.reason))
        # We keep seeing the correct exception on subsequent requests.
        self.assertEqual(503, self.getHTTPError(url).code)
        # When the database is available again, requests succeed.
        bouncer.start()
        # bouncer.start() can sometimes return before the service is actually
        # available for use.  To be defensive, let's retry a few times.  See
        # bug 974617.
        retries = 5
        for i in xrange(retries):
            try:
                urllib2.urlopen(url)
            except urllib2.HTTPError as e:
                if e.code != httplib.SERVICE_UNAVAILABLE:
                    raise
            else:
                break
            time.sleep(0.5)
        else:
            raise TimeoutException(
                "bouncer did not come up after {} attempts.".format(retries))



    def test_operationalerror_view(self):
        request = LaunchpadTestRequest()
        OperationalErrorView(OperationalError(), request)
        self.assertEquals(503, request.response.getStatus())
