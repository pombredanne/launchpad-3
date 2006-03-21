# Copyright 2006 Canonical Ltd.  All rights reserved.
"""distributionmirror-prober tests."""

__metaclass__ = type


import os
import httplib
from StringIO import StringIO
from unittest import TestCase, TestLoader

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure
from twisted.trial.unittest import TestCase as TwistedTestCase
from twisted.web import server

from sqlobject import SQLObjectNotFound

import canonical
from canonical.config import config
from canonical.lp import initZopeless
from canonical.lp.dbschema import PackagePublishingPocket
from canonical.launchpad.daemons.tachandler import TacTestSetup
from canonical.launchpad.database import DistributionMirror, DistroRelease
from canonical.launchpad.ftests.harness import LaunchpadTestSetup
from canonical.launchpad.scripts.distributionmirror_prober import (
    ProberFactory, ProberTimeout, MirrorProberCallbacks,
    BadResponseCodeException)
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


class TestDistributionMirrorProber(TwistedTestCase):

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

    def _createProberAndConnect(self, url):
        prober = ProberFactory(url)
        reactor.connectTCP(prober.host, prober.port, prober)
        return prober.deferred

    def test_200(self):
        d = self._createProberAndConnect(self.urls['200'])
        def got_result(result):
            self.failUnless(
                result == str(httplib.OK),
                "Expected a '200' status but got '%s'" % result)
        return d.addCallback(got_result)

    def test_notfound(self):
        d = self._createProberAndConnect(self.urls['404'])
        return self.assertFailure(d, BadResponseCodeException)

    def test_500(self):
        d = self._createProberAndConnect(self.urls['500'])
        return self.assertFailure(d, ProberTimeout)
        return self.assertFailure(d, BadResponseCodeException)

    def test_timeout(self):
        d = self._createProberAndConnect(self.urls['timeout'])
        return self.assertFailure(d, ProberTimeout)


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

        d = Deferred()
        d.addErrback(callbacks.deleteMirrorRelease)
        def got_result(result):
            self.fail(
                "Any failure that's not a timeout should be propagated.")
        ok = []
        def got_failure(failure):
            ok.append(1)
        d.addCallbacks(got_result, got_failure)
        d.errback(Failure(ZeroDivisionError()))
        self.assertEqual([1], ok)

        mirror_distro_release_source = None
        mirror_distro_release_source = callbacks.ensureOrDeleteMirrorRelease(
             str(httplib.OK))
        self.failUnless(
            mirror_distro_release_source is not None,
            "If the prober gets a 200 Okay status, a new "
            "MirrorDistroReleaseSource/MirrorDistroArchRelease should be "
            "created.")

        callbacks.deleteMirrorRelease(
            Failure(BadResponseCodeException(str(httplib.NOT_FOUND))))
        # If the prober gets a 404 status, we need to make sure there's no
        # MirrorDistroReleaseSource/MirrorDistroArchRelease referent to
        # that url
        self.assertRaises(
            SQLObjectNotFound, mirror_distro_release_source.sync)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
