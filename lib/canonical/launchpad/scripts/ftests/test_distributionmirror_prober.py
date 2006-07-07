# Copyright 2006 Canonical Ltd.  All rights reserved.
"""distributionmirror-prober tests."""

__metaclass__ = type


import os
import httplib
from StringIO import StringIO
from unittest import TestCase, TestLoader

from twisted.internet import reactor, defer
from twisted.python.failure import Failure
from twisted.web import server

from sqlobject import SQLObjectNotFound

import canonical
from canonical.config import config
from canonical.lp import initZopeless
from canonical.lp.dbschema import PackagePublishingPocket
from canonical.launchpad.daemons.tachandler import TacTestSetup
from canonical.launchpad.database import DistributionMirror, DistroRelease
from canonical.launchpad.ftests.harness import LaunchpadTestSetup
from canonical.tests.test_twisted import TwistedTestCase
from canonical.launchpad.scripts.distributionmirror_prober import (
    ProberFactory, MirrorProberCallbacks, BadResponseCode,
    MirrorCDImageProberCallbacks, ProberTimeout, RedirectAwareProberFactory)
from canonical.launchpad.scripts.ftests.distributionmirror_http_server import (
    DistributionMirrorTestHTTPServer)
from canonical.functional import ZopelessLayer


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
        self.unchecked_urls = self.urls.values()
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
        prober = RedirectAwareProberFactory(
            'http://localhost:11375/redirectme')
        self.failUnless(
            prober.seen_urls == ['http://localhost:11375/redirectme'])
        deferred = prober.probe()
        def got_result(result):
            self.failUnless(
                prober.seen_urls == ['http://localhost:11375/redirectme',
                                     'http://localhost:11375/valid-mirror'])
        return deferred.addBoth(got_result)

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


class TestMirrorCDImageProberCallbacks(TestCase):
    layer = ZopelessLayer

    def setUp(self):
        LaunchpadTestSetup().setUp()
        self.ztm = initZopeless(dbuser=config.distributionmirrorprober.dbuser)
        mirror = DistributionMirror.get(1)
        warty = DistroRelease.get(1)
        flavour = 'ubuntu'
        log_file = StringIO()
        self.callbacks = MirrorCDImageProberCallbacks(
            mirror, warty, flavour, log_file)

    def tearDown(self):
        LaunchpadTestSetup().tearDown()
        self.ztm.uninstall()

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


class TestMirrorProberCallbacks(TestCase):
    layer = ZopelessLayer

    def setUp(self):
        LaunchpadTestSetup().setUp()
        self.ztm = initZopeless(dbuser=config.distributionmirrorprober.dbuser)
        mirror = DistributionMirror.get(1)
        warty = DistroRelease.get(1)
        pocket = PackagePublishingPocket.RELEASE
        component = warty.components[0]
        log_file = StringIO()
        url = 'foo'
        self.callbacks = MirrorProberCallbacks(
            mirror, warty, pocket, component, url, log_file)

    def tearDown(self):
        LaunchpadTestSetup().tearDown()
        self.ztm.uninstall()

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


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
