# Copyright 2006 Canonical Ltd.  All rights reserved.
"""distributionmirror-prober tests."""

__metaclass__ = type


import os
import time
import signal
import httplib
from StringIO import StringIO
from subprocess import Popen
from unittest import TestCase, TestSuite, makeSuite

from twisted.internet import reactor
from twisted.python.failure import Failure

from canonical.config import config
from canonical.lp import initZopeless
from canonical.lp.dbschema import PackagePublishingPocket
from canonical.launchpad.database import DistributionMirror, DistroRelease
from canonical.launchpad.ftests.harness import LaunchpadTestSetup
from canonical.launchpad.scripts.distributionmirror_prober import (
    ProberFactory, ProberTimeout, MirrorProberCallbacks)


class TestDistributionMirrorProber(TestCase):

    def setUp(self):
        self.urls = {'timeout': u'http://foo.fdafdabar.fds/pub/ubuntu',
                     '200': u'http://localhost:11375/valid-mirror/',
                     '404': u'http://localhost:11375/invalid-mirror/'}
        self.unchecked_urls = self.urls.values()
        self.easygoing = Popen(
            'lib/canonical/launchpad/scripts/ftests/easygoing_http.py')
        # Wait two second to make sure the easygoing http server will be
        # running when we need it.
        # XXX: This is not reliable at all. We need a way to check that the
        # script is actually running.
        time.sleep(2)

    def _createProberAndConnect(self, url, callback=None, errback=None):
        prober = ProberFactory(url)
        if callback is not None:
            prober.deferred.addCallback(callback)
        if errback is not None:
            prober.deferred.addErrback(errback)
        prober.deferred.addBoth(self.finish, url)
        reactor.connectTCP(prober.host, prober.port, prober)

    def finish(self, result, url):
        self.unchecked_urls.remove(url)
        if not len(self.unchecked_urls):
            reactor.callLater(0, reactor.stop)

    def timeout_errback(self, reason):
        self.timeout_reason = reason

    def okay_callback(self, status):
        self.okay_status = status

    def notfound_callback(self, status):
        self.notfound_status = status

    def test_everything(self):
        reactor.callLater(0, self.t_timeout)
        reactor.callLater(0, self.t_200)
        reactor.callLater(0, self.t_notfound)
        reactor.run()
        os.kill(self.easygoing.pid, signal.SIGINT)
        self.failUnless(self.timeout_reason.type is ProberTimeout,
                        "Expected a timeout but got %r" % self.timeout_reason)
        self.failUnless(
            self.okay_status == str(httplib.OK), 
            "Expected a '200' status but got '%s'" % self.okay_status)
        self.failUnless(
            self.notfound_status == str(httplib.NOT_FOUND),
            "Expected a '404' status but got '%s'" % self.notfound_status)

    def t_200(self):
        self.okay_status = None
        url = self.urls['200']
        self._createProberAndConnect(url, callback=self.okay_callback)

    def t_notfound(self):
        self.notfound_status = None
        url = self.urls['404']
        self._createProberAndConnect(url, callback=self.notfound_callback)

    def t_timeout(self):
        self.timeout_reason = None
        url = self.urls['timeout']
        self._createProberAndConnect(url, errback=self.timeout_errback)


class TestDistributionMirrorProberCallbacks(TestCase):

    def setUp(self):
        LaunchpadTestSetup().setUp()
        self.ztm = initZopeless(dbuser=config.distributionmirrorprober.dbuser)

    def tearDown(self):
        LaunchpadTestSetup().tearDown()
        self.ztm.uninstall()

    def test_Callbacks(self):
        mirror = DistributionMirror.get(1)
        warty = DistroRelease.get(1)
        pocket = PackagePublishingPocket.RELEASE
        component = warty.components[0]
        log_file = StringIO()
        url = 'foo'
        callbacks = MirrorProberCallbacks(
            mirror, warty, pocket, component, url, log_file)
        reason = callbacks.deleteMirrorRelease(
            Failure(exc_value=ProberTimeout()))
        self.failUnless(
            reason is None, "A timeout shouldn't be propagated.")

        reason = callbacks.deleteMirrorRelease(Failure())
        self.failUnless(
            reason is not None, 
            "Any failure that's not a timeout should be propagated.")

        mirror_distro_release_source = None
        mirror_distro_release_source = callbacks.ensureOrDeleteMirrorRelease(
             str(httplib.OK))
        self.failUnless(
            mirror_distro_release_source is not None,
            "If the prober gets a 200 Okay status, a new "
            "MirrorDistroReleaseSource/MirrorDistroArchRelease should be "
            "created.")

        mirror_distro_release_source = callbacks.ensureOrDeleteMirrorRelease(
            str(httplib.NOT_FOUND))
        self.failUnless(
            mirror_distro_release_source is None,
            "If the prober gets a 404 status, we need to make sure there's no "
            "MirrorDistroReleaseSource/MirrorDistroArchRelease referent to "
            "that url")


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(TestDistributionMirrorProber))
    suite.addTest(makeSuite(TestDistributionMirrorProberCallbacks))
    return suite
