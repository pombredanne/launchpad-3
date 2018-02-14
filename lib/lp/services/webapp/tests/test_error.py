# Copyright 2011-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test error views."""


import httplib
import logging
import socket
import time
import urllib2

from fixtures import FakeLogger
import psycopg2
from storm.exceptions import (
    DisconnectionError,
    OperationalError,
    )
from testtools.content import Content
from testtools.content_type import UTF8_TEXT
from testtools.matchers import (
    Equals,
    MatchesAny,
    MatchesListwise,
    )
import transaction
from zope.app.testing import ztapi

from lp.services.webapp.error import (
    DisconnectionErrorView,
    OperationalErrorView,
    SystemErrorView,
    )
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.testing import TestCase
from lp.testing.fixture import (
    CaptureOops,
    PGBouncerFixture,
    Urllib2Fixture,
    )
from lp.testing.layers import (
    DatabaseLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.matchers import Contains


class TimeoutException(Exception):
    pass


class TestSystemErrorView(TestCase):

    layer = LaunchpadFunctionalLayer

    def test_without_oops_id(self):
        request = LaunchpadTestRequest()
        SystemErrorView(Exception(), request)
        self.assertEqual(500, request.response.getStatus())
        self.assertIsNone(
            request.response.getHeader('X-Lazr-OopsId', literal=True))

    def test_with_oops_id(self):
        request = LaunchpadTestRequest()
        request.oopsid = 'OOPS-1X1'
        SystemErrorView(Exception(), request)
        self.assertEqual(500, request.response.getStatus())
        self.assertEqual(
            'OOPS-1X1',
            request.response.getHeader('X-Lazr-OopsId', literal=True))


class TestDatabaseErrorViews(TestCase):

    layer = LaunchpadFunctionalLayer

    def getHTTPError(self, url):
        try:
            urllib2.urlopen(url)
        except urllib2.HTTPError as error:
            return error
        else:
            self.fail("We should have gotten an HTTP error")

    def add_retry_failure_details(self, bouncer):
        # XXX benji bug=974617, bug=1011847, bug=504291 2011-07-31:
        # This method (and its invocations) are to be removed when we have
        # figured out what is causing bug 974617 and friends.

        # First we figure out if pgbouncer is listening on the port it is
        # supposed to be listening on.  connect_ex returns 0 on success or an
        # errno otherwise.
        pg_port_status = str(socket.socket().connect_ex(('localhost', 5432)))
        self.addDetail('postgres socket.connect_ex result',
            Content(UTF8_TEXT, lambda: pg_port_status))
        bouncer_port_status = str(
            socket.socket().connect_ex(('localhost', bouncer.port)))
        self.addDetail('pgbouncer socket.connect_ex result',
            Content(UTF8_TEXT, lambda: bouncer_port_status))

    def retryConnection(self, url, bouncer, retries=60):
        """Retry to connect to *url* for *retries* times.

        Return the file-like object returned by *urllib2.urlopen(url)*.
        Raise a TimeoutException if the connection can not be established.
        """
        for i in range(retries):
            try:
                return urllib2.urlopen(url)
            except urllib2.HTTPError as e:
                if e.code != httplib.SERVICE_UNAVAILABLE:
                    raise
            time.sleep(1)
        else:
            self.add_retry_failure_details(bouncer)
            raise TimeoutException(
                "Launchpad did not come up after {0} attempts."
                    .format(retries))

    def test_disconnectionerror_view_integration(self):
        # Test setup.
        self.useFixture(FakeLogger('SiteError', level=logging.CRITICAL))
        self.useFixture(Urllib2Fixture())
        bouncer = PGBouncerFixture()
        # XXX gary bug=974617, bug=1011847, bug=504291 2011-07-03:
        # In parallel tests, we are rarely encountering instances of
        # bug 504291 while running this test.  These cause the tests
        # to fail entirely (the store.rollback() described in comment
        # 11 does not fix the insane state) despite nultiple retries.
        # As mentioned in that bug, we are trying aborts to see if they
        # eliminate the problem.  If this works, we can find which of
        # these two aborts are actually needed.
        transaction.abort()
        self.useFixture(bouncer)
        transaction.abort()
        # Verify things are working initially.
        url = 'http://launchpad.dev/'
        self.retryConnection(url, bouncer)
        # Now break the database, and we get an exception, along with
        # our view and several OOPSes from the retries.
        bouncer.stop()

        class Disconnects(Equals):
            def __init__(self, message):
                super(Disconnects, self).__init__(
                    ('DisconnectionError', message))

        with CaptureOops() as oopses:
            error = self.getHTTPError(url)
        self.assertEqual(503, error.code)
        self.assertThat(error.read(),
                        Contains(DisconnectionErrorView.reason))
        self.assertThat(
            [(oops['type'], oops['value'].split('\n')[0])
             for oops in oopses.oopses],
            MatchesListwise(
                [MatchesAny(
                    # libpq < 9.5.
                    Disconnects('error with no message from the libpq'),
                    # libpq >= 9.5.
                    Disconnects('server closed the connection unexpectedly'))]
                * 2 +
                [Disconnects(
                    'could not connect to server: Connection refused')]
                * 6))

        # We keep seeing the correct exception on subsequent requests.
        with CaptureOops() as oopses:
            error = self.getHTTPError(url)
        self.assertEqual(503, error.code)
        self.assertThat(error.read(),
                        Contains(DisconnectionErrorView.reason))
        self.assertThat(
            [(oops['type'], oops['value'].split('\n')[0])
             for oops in oopses.oopses],
            MatchesListwise(
                [Disconnects(
                    'could not connect to server: Connection refused')]
                * 8))

        # When the database is available again, requests succeed.
        bouncer.start()
        self.retryConnection(url, bouncer)

        # If we ask pgbouncer to disable the database, requests fail and
        # get the same error page, but we don't log OOPSes except for
        # the initial connection terminations. Disablement is always
        # explicit maintenance, and we don't need lots of ongoing OOPSes
        # to tell us about maintenance that we're doing.
        dbname = DatabaseLayer._db_fixture.dbname
        conn = psycopg2.connect("dbname=pgbouncer")
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("DISABLE " + dbname)
        cur.execute("KILL " + dbname)
        cur.execute("RESUME " + dbname)

        with CaptureOops() as oopses:
            error = self.getHTTPError(url)
        self.assertEqual(503, error.code)
        self.assertThat(error.read(),
                        Contains(DisconnectionErrorView.reason))
        self.assertThat(
            [(oops['type'], oops['value'].split('\n')[0])
             for oops in oopses.oopses],
            MatchesListwise([Disconnects('database removed')]))

        # A second request doesn't log any OOPSes.
        with CaptureOops() as oopses:
            error = self.getHTTPError(url)
        self.assertEqual(503, error.code)
        self.assertThat(error.read(),
                        Contains(DisconnectionErrorView.reason))
        self.assertEqual(
            [],
            [(oops['type'], oops['value'].split('\n')[0])
             for oops in oopses.oopses])

        # When the database is available again, requests succeed.
        cur.execute("ENABLE %s" % DatabaseLayer._db_fixture.dbname)
        self.retryConnection(url, bouncer)

    def test_disconnectionerror_view(self):
        request = LaunchpadTestRequest()
        DisconnectionErrorView(DisconnectionError(), request)
        self.assertEqual(503, request.response.getStatus())

    def test_operationalerror_view_integration(self):
        # Test setup.
        self.useFixture(FakeLogger('SiteError', level=logging.CRITICAL))
        self.useFixture(Urllib2Fixture())

        class BrokenView(object):
            """A view that raises an OperationalError"""
            def __call__(self, *args, **kw):
                raise OperationalError()
        ztapi.browserView(None, "error-test", BrokenView())

        url = 'http://launchpad.dev/error-test'
        error = self.getHTTPError(url)
        self.assertEqual(httplib.SERVICE_UNAVAILABLE, error.code)
        self.assertThat(error.read(),
                        Contains(OperationalErrorView.reason))

    def test_operationalerror_view(self):
        request = LaunchpadTestRequest()
        OperationalErrorView(OperationalError(), request)
        self.assertEqual(503, request.response.getStatus())
