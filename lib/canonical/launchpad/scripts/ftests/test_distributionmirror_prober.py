# Copyright 2006 Canonical Ltd.  All rights reserved.
"""distributionmirror-prober tests."""

__metaclass__ = type


import httplib
import logging
import os
from StringIO import StringIO
from unittest import TestCase, TestLoader

from twisted.internet import reactor, defer
from twisted.python.failure import Failure
from twisted.web import server

from sqlobject import SQLObjectNotFound

import canonical
from canonical.config import config
from canonical.lp.dbschema import PackagePublishingPocket
from canonical.launchpad.webapp.uri import URI
from canonical.launchpad.daemons.tachandler import TacTestSetup
from canonical.launchpad.database import DistributionMirror, DistroRelease
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestCase
from canonical.tests.test_twisted import TwistedTestCase
from canonical.launchpad.scripts.distributionmirror_prober import (
    ProberFactory, MirrorProberCallbacks, BadResponseCode,
    MirrorCDImageProberCallbacks, ProberTimeout, RedirectAwareProberFactory,
    InfiniteLoopDetected, UnknownURLScheme, MAX_REDIRECTS,
    RedirectAwareProberProtocol, probe_archive_mirror, probe_release_mirror)
from canonical.launchpad.scripts.ftests.distributionmirror_http_server import (
    DistributionMirrorTestHTTPServer)


class HTTPServerTestSetup(TacTestSetup):

    def setUpRoot(self):
        pass

    @property
    def root(self):
        return '/var/tmp'

    @property
    def tacfile(self):
        return os.path.abspath(os.path.join(
            os.path.dirname(canonical.__file__), os.pardir, os.pardir,
            'daemons/distributionmirror_http_server.tac'
            ))

    @property
    def pidfile(self):
        return os.path.join(self.root, 'distributionmirror_http_server.pid')

    @property
    def logfile(self):
        return os.path.join(self.root, 'distributionmirror_http_server.log')


class TestProberProtocol(TwistedTestCase):

    def setUp(self):
        self.urls = {'timeout': u'http://localhost:11375/timeout',
                     '200': u'http://localhost:11375/valid-mirror',
                     '500': u'http://localhost:11375/error',
                     '404': u'http://localhost:11375/invalid-mirror'}
        root = DistributionMirrorTestHTTPServer()
        site = server.Site(root)
        site.displayTracebacks = False
        self.port = reactor.listenTCP(11375, site)

    def tearDown(self):
        return self.port.stopListening()

    def _createProberAndProbe(self, url):
        prober = ProberFactory(url)
        return prober.probe()

    def test_probe_sets_up_timeout_call(self):
        prober = ProberFactory(self.urls['200'])
        self.failUnless(getattr(prober, 'timeoutCall', None) is None)
        deferred = prober.probe()
        self.failUnless(getattr(prober, 'timeoutCall', None) is not None)
        return deferred

    def test_redirectawareprober_follows_http_redirect(self):
        url = 'http://localhost:11375/redirect-to-valid-mirror'
        prober = RedirectAwareProberFactory(url)
        self.failUnless(prober.redirection_count == 0)
        self.failUnless(
            prober.url == 'http://localhost:11375/redirect-to-valid-mirror')
        deferred = prober.probe()
        def got_result(result):
            self.failUnless(prober.redirection_count == 1)
            self.failUnless(
                prober.url == 'http://localhost:11375/valid-mirror')
            self.failUnless(result == str(httplib.OK))
        return deferred.addCallback(got_result)

    def test_redirectawareprober_detects_infinite_loop(self):
        prober = RedirectAwareProberFactory(
            'http://localhost:11375/redirect-infinite-loop')
        deferred = prober.probe()
        return self.assertFailure(deferred, InfiniteLoopDetected)

    def test_redirectawareprober_fail_on_unknown_scheme(self):
        prober = RedirectAwareProberFactory(
            'http://localhost:11375/redirect-unknown-url-scheme')
        deferred = prober.probe()
        return self.assertFailure(deferred, UnknownURLScheme)

    def test_200(self):
        d = self._createProberAndProbe(self.urls['200'])
        def got_result(result):
            self.failUnless(
                result == str(httplib.OK),
                "Expected a '200' status but got '%s'" % result)
        return d.addCallback(got_result)

    def test_success_cancel_timeout_call(self):
        prober = ProberFactory(self.urls['200'])
        deferred = prober.probe()
        self.failUnless(prober.timeoutCall.active())
        def check_timeout_call(result):
            self.failIf(prober.timeoutCall.active())
        return deferred.addCallback(check_timeout_call)

    def test_failure_cancel_timeout_call(self):
        prober = ProberFactory(self.urls['500'])
        deferred = prober.probe()
        self.failUnless(prober.timeoutCall.active())
        def check_timeout_call(result):
            self.failIf(prober.timeoutCall.active())
        return deferred.addErrback(check_timeout_call)

    def test_notfound(self):
        d = self._createProberAndProbe(self.urls['404'])
        return self.assertFailure(d, BadResponseCode)

    def test_500(self):
        d = self._createProberAndProbe(self.urls['500'])
        return self.assertFailure(d, BadResponseCode)

    def test_timeout(self):
        d = self._createProberAndProbe(self.urls['timeout'])
        return self.assertFailure(d, ProberTimeout)


class FakeTimeOutCall:
    resetCalled = False

    def reset(self, seconds):
        self.resetCalled = True


class FakeTransport:
    disconnecting = False

    def loseConnection(self):
        self.disconnecting = True

    def write(self, text):
        pass


class FakeFactory(RedirectAwareProberFactory):
    redirectedTo = None

    def redirect(self, url):
        self.redirectedTo = url


class TestRedirectAwareProberFactoryAndProtocol(TestCase):

    def test_redirect_resets_timeout(self):
        prober = RedirectAwareProberFactory('http://foo.bar')
        prober.timeoutCall = FakeTimeOutCall()
        prober.connect = lambda: None
        self.failIf(prober.timeoutCall.resetCalled)
        prober.redirect('http://localhost:11375/valid-mirror')
        self.failUnless(prober.timeoutCall.resetCalled)

    def _createFactoryAndStubConnectAndTimeoutCall(self):
        prober = RedirectAwareProberFactory('http://foo.bar')
        prober.timeoutCall = FakeTimeOutCall()
        prober.connectCalled = False
        def connect():
            prober.connectCalled = True
        prober.connect = connect
        return prober

    def test_noconnection_is_made_when_infiniteloop_detected(self):
        prober = self._createFactoryAndStubConnectAndTimeoutCall()
        prober.failed = lambda error: None
        prober.redirection_count = MAX_REDIRECTS
        prober.redirect('http://localhost:11375/valid-mirror')
        self.failIf(prober.connectCalled)

    def test_noconnection_is_made_when_url_scheme_is_not_http_or_ftp(self):
        prober = self._createFactoryAndStubConnectAndTimeoutCall()
        prober.failed = lambda error: None
        prober.redirect('ssh://localhost/valid-mirror')
        self.failIf(prober.connectCalled)

    def test_connection_is_made_on_successful_redirect(self):
        prober = self._createFactoryAndStubConnectAndTimeoutCall()
        prober.redirect('http://localhost:11375/valid-mirror')
        self.failUnless(prober.connectCalled)

    def test_connection_is_closed_on_redirect(self):
        protocol = RedirectAwareProberProtocol()
        protocol.factory = FakeFactory('http://foo.bar/')
        protocol.makeConnection(FakeTransport())
        protocol.dataReceived(
            "HTTP/1.1 301 Moved Permanently\r\n"
            "Location: http://foo.baz/\r\n"
            "Length: 0\r\n"
            "\r\n")
        self.assertEqual('http://foo.baz/', protocol.factory.redirectedTo)
        self.failUnless(protocol.transport.disconnecting)


class TestMirrorCDImageProberCallbacks(LaunchpadZopelessTestCase):
    dbuser = config.distributionmirrorprober.dbuser

    def setUp(self):
        mirror = DistributionMirror.get(1)
        warty = DistroRelease.get(1)
        flavour = 'ubuntu'
        log_file = StringIO()
        self.callbacks = MirrorCDImageProberCallbacks(
            mirror, warty, flavour, log_file)

    def test_mirrorcdimagerelease_creation_and_deletion(self):
        callbacks = self.callbacks
        all_success = [(defer.SUCCESS, '200'), (defer.SUCCESS, '200')]
        mirror_cdimage_release = callbacks.ensureOrDeleteMirrorCDImageRelease(
             all_success)
        self.failUnless(
            mirror_cdimage_release is not None,
            "If the prober gets a list of 200 Okay statuses, a new "
            "MirrorCDImageRelease should be created.")

        not_all_success = [
            (defer.FAILURE, Failure(BadResponseCode(str(httplib.NOT_FOUND)))),
            (defer.SUCCESS, '200')]
        callbacks.ensureOrDeleteMirrorCDImageRelease(not_all_success)
        # If the prober gets at least one 404 status, we need to make sure
        # there's no MirrorCDImageRelease for that release and flavour.
        self.assertRaises(SQLObjectNotFound, mirror_cdimage_release.sync)

    def test_timeout_is_not_propagated(self):
        # Make sure that ensureOrDeleteMirrorCDImageRelease() does not 
        # propagate ProberTimeout
        failure = self.callbacks.ensureOrDeleteMirrorCDImageRelease(
            [(defer.FAILURE, Failure(ProberTimeout('http://localhost/', 5)))])
        # Twisted callbacks may raise or return a failure; that's why we check
        # the return value
        self.failIf(isinstance(failure, Failure))

    def test_badresponse_is_not_propagated(self):
        # Make sure that ensureOrDeleteMirrorCDImageRelease() does not 
        # propagate BadResponseCode failures.
        failure = self.callbacks.ensureOrDeleteMirrorCDImageRelease(
            [(defer.FAILURE,
              Failure(BadResponseCode(str(httplib.NOT_FOUND))))])
        # Twisted callbacks may raise or return a failure; that's why we check
        # the return value
        self.failIf(isinstance(failure, Failure))

    def test_anything_but_timeouts_and_badresponses_are_propagated(self):
        # Any failure that is not a ProberTimeout or a BadResponseCode
        # should be propagated.
        self.assertRaises(
            Failure, self.callbacks.ensureOrDeleteMirrorCDImageRelease,
            [(defer.FAILURE, Failure(ZeroDivisionError()))])


class TestMirrorProberCallbacks(LaunchpadZopelessTestCase):

    def setUp(self):
        mirror = DistributionMirror.get(1)
        warty = DistroRelease.get(1)
        pocket = PackagePublishingPocket.RELEASE
        component = warty.components[0]
        log_file = StringIO()
        url = 'foo'
        self.callbacks = MirrorProberCallbacks(
            mirror, warty, pocket, component, url, log_file)

    def test_failure_propagation(self):
        # Make sure that deleteMirrorRelease() does not propagate
        # ProberTimeout or BadResponseCode failures.
        try:
            self.callbacks.deleteMirrorRelease(
                Failure(ProberTimeout('http://localhost/', 5)))
        except Exception, e:
            self.fail("A timeout shouldn't be propagated. Got %s" % e)
        try:
            self.callbacks.deleteMirrorRelease(
                Failure(BadResponseCode(str(httplib.INTERNAL_SERVER_ERROR))))
        except Exception, e:
            self.fail("A bad response code shouldn't be propagated. Got %s" % e)

        # Make sure that deleteMirrorRelease() propagate any failure that is
        # not a ProberTimeout or BadResponseCode.
        d = defer.Deferred()
        d.addErrback(self.callbacks.deleteMirrorRelease)
        def got_result(result):
            self.fail(
                "Any failure that's not a timeout should be propagated.")
        ok = []
        def got_failure(failure):
            ok.append(1)
        d.addCallbacks(got_result, got_failure)
        d.errback(Failure(ZeroDivisionError()))
        self.assertEqual([1], ok)

    def test_mirrorrelease_creation_and_deletion(self):
        mirror_distro_release_source = self.callbacks.ensureMirrorRelease(
             str(httplib.OK))
        self.failUnless(
            mirror_distro_release_source is not None,
            "If the prober gets a 200 Okay status, a new "
            "MirrorDistroReleaseSource/MirrorDistroArchRelease should be "
            "created.")

        self.callbacks.deleteMirrorRelease(
            Failure(BadResponseCode(str(httplib.NOT_FOUND))))
        # If the prober gets a 404 status, we need to make sure there's no
        # MirrorDistroReleaseSource/MirrorDistroArchRelease referent to
        # that url
        self.assertRaises(
            SQLObjectNotFound, mirror_distro_release_source.sync)


class TestProbeFunctionSemaphores(LaunchpadZopelessTestCase):
    """Make sure we use one DeferredSemaphore for each hostname when probing
    mirrors.
    """

    def setUp(self):
        self.logger = None

    def test_archive_mirror_probe_function(self):
        mirror1 = DistributionMirror.byName('archive-mirror')
        mirror2 = DistributionMirror.byName('archive-mirror2')
        mirror3 = DistributionMirror.byName('canonical-archive')
        self._test_one_semaphore_for_each_host(
            mirror1, mirror2, mirror3, probe_archive_mirror)

    def test_release_mirror_probe_function(self):
        mirror1 = DistributionMirror.byName('releases-mirror')
        mirror2 = DistributionMirror.byName('releases-mirror2')
        mirror3 = DistributionMirror.byName('canonical-releases')
        self._test_one_semaphore_for_each_host(
            mirror1, mirror2, mirror3, probe_release_mirror)

    def _test_one_semaphore_for_each_host(
            self, mirror1, mirror2, mirror3, probe_function):
        """Check that we create one semaphore per host when probing the given
        mirrors using the given probe_function.

        mirror1.base_url and mirror2.base_url must be on the same host while
        mirror3.base_url must be on a different one.

        The given probe_function must be either probe_release_mirror or
        probe_archive_mirror.
        """
        host_semaphores = {}
        mirror1_host = URI(mirror1.base_url).host
        mirror2_host = URI(mirror2.base_url).host
        mirror3_host = URI(mirror3.base_url).host

        probe_function(
            mirror1, StringIO(), [], logging, host_semaphores=host_semaphores)
        # Since we have a single mirror to probe we need to have a single
        # Deferred with a limit of 1, to ensure we don't issue simultaneous
        # connections on that mirror.
        self.assertEquals(len(host_semaphores), 1)
        self.assertEquals(host_semaphores[mirror1_host].limit, 1)

        probe_function(
            mirror2, StringIO(), [], logging, host_semaphores=host_semaphores)
        # Now we have two mirrors to probe, but they have the same hostname,
        # so we'll still have a single semaphore in host_semaphores.
        self.assertEquals(mirror2_host, mirror1_host)
        self.assertEquals(len(host_semaphores), 1)
        self.assertEquals(host_semaphores[mirror1_host].limit, 1)

        probe_function(
            mirror3, StringIO(), [], logging, host_semaphores=host_semaphores)
        # This third mirror is on a separate host, so we'll have a second
        # semaphore added to host_semaphores.
        self.failUnless(mirror3_host != mirror1_host)
        self.assertEquals(len(host_semaphores), 2)
        self.assertEquals(host_semaphores[mirror3_host].limit, 1)



def test_suite():
    return TestLoader().loadTestsFromName(__name__)
