# Copyright 2015-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test snap package build behaviour."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

import base64
from datetime import datetime
import json
import os.path
from textwrap import dedent
import time
import uuid

import fixtures
from pymacaroons import Macaroon
import pytz
from six.moves.urllib_parse import urlsplit
from testtools import ExpectedException
from testtools.matchers import (
    AfterPreprocessing,
    ContainsDict,
    Equals,
    HasLength,
    Is,
    IsInstance,
    MatchesDict,
    MatchesListwise,
    MatchesStructure,
    StartsWith,
    )
from testtools.twistedsupport import (
    AsynchronousDeferredRunTestForBrokenTwisted,
    )
import transaction
from twisted.internet import (
    defer,
    endpoints,
    reactor,
    )
from twisted.python.compat import nativeString
from twisted.trial.unittest import TestCase as TrialTestCase
from twisted.web import (
    resource,
    server,
    xmlrpc,
    )
from zope.component import getUtility
from zope.proxy import isProxy
from zope.publisher.xmlrpc import TestRequest
from zope.security.proxy import removeSecurityProxy

from lp.app.enums import InformationType
from lp.archivepublisher.interfaces.archivesigningkey import (
    IArchiveSigningKey,
    )
from lp.buildmaster.enums import (
    BuildBaseImageType,
    BuildStatus,
    )
from lp.buildmaster.interfaces.builder import CannotBuild
from lp.buildmaster.interfaces.buildfarmjobbehaviour import (
    IBuildFarmJobBehaviour,
    )
from lp.buildmaster.interfaces.processor import IProcessorSet
from lp.buildmaster.tests.mock_slaves import (
    MockBuilder,
    OkSlave,
    SlaveTestHelpers,
    )
from lp.buildmaster.tests.test_buildfarmjobbehaviour import (
    TestGetUploadMethodsMixin,
    TestHandleStatusMixin,
    TestVerifySuccessfulBuildMixin,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.services.authserver.xmlrpc import AuthServerAPIView
from lp.services.config import config
from lp.services.features.testing import FeatureFixture
from lp.services.log.logger import (
    BufferLogger,
    DevNullLogger,
    )
from lp.services.webapp import canonical_url
from lp.snappy.interfaces.snap import (
    SNAP_PRIVATE_FEATURE_FLAG,
    SNAP_SNAPCRAFT_CHANNEL_FEATURE_FLAG,
    SnapBuildArchiveOwnerMismatch,
    )
from lp.snappy.model.snapbuildbehaviour import (
    format_as_rfc3339,
    SnapBuildBehaviour,
    )
from lp.soyuz.adapters.archivedependencies import (
    get_sources_list_for_building,
    )
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.interfaces.archive import ArchiveDisabled
from lp.soyuz.tests.soyuz import Base64KeyMatches
from lp.testing import (
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.dbuser import dbuser
from lp.testing.gpgkeys import gpgkeysdir
from lp.testing.keyserver import InProcessKeyServerFixture
from lp.testing.layers import LaunchpadZopelessLayer
from lp.xmlrpc.interfaces import IPrivateApplication


class ProxyAuthAPITokensResource(resource.Resource):
    """A test tokens resource for the proxy authentication API."""

    isLeaf = True

    def __init__(self):
        resource.Resource.__init__(self)
        self.requests = []

    def render_POST(self, request):
        content = request.content.read()
        self.requests.append({
            "method": request.method,
            "uri": request.uri,
            "headers": dict(request.requestHeaders.getAllRawHeaders()),
            "content": content,
            })
        username = json.loads(content)["username"]
        return json.dumps({
            "username": username,
            "secret": uuid.uuid4().hex,
            "timestamp": datetime.utcnow().isoformat(),
            })


class InProcessProxyAuthAPIFixture(fixtures.Fixture):
    """A fixture that pretends to be the proxy authentication API.

    Users of this fixture must call the `start` method, which returns a
    `Deferred`, and arrange for that to get back to the reactor.  This is
    necessary because the basic fixture API does not allow `setUp` to return
    anything.  For example:

        class TestSomething(TestCase):

            run_tests_with = AsynchronousDeferredRunTest.make_factory(
                timeout=10)

            @defer.inlineCallbacks
            def setUp(self):
                super(TestSomething, self).setUp()
                yield self.useFixture(InProcessProxyAuthAPIFixture()).start()
    """

    @defer.inlineCallbacks
    def start(self):
        root = resource.Resource()
        self.tokens = ProxyAuthAPITokensResource()
        root.putChild("tokens", self.tokens)
        endpoint = endpoints.serverFromString(reactor, nativeString("tcp:0"))
        site = server.Site(self.tokens)
        self.addCleanup(site.stopFactory)
        port = yield endpoint.listen(site)
        self.addCleanup(port.stopListening)
        config.push("in-process-proxy-auth-api-fixture", dedent("""
            [snappy]
            builder_proxy_auth_api_admin_secret: admin-secret
            builder_proxy_auth_api_endpoint: http://%s:%s/tokens
            """) %
            (port.getHost().host, port.getHost().port))
        self.addCleanup(config.pop, "in-process-proxy-auth-api-fixture")


class InProcessAuthServer(xmlrpc.XMLRPC):

    def __init__(self, *args, **kwargs):
        xmlrpc.XMLRPC.__init__(self, *args, **kwargs)
        private_root = getUtility(IPrivateApplication)
        self.authserver = AuthServerAPIView(
            private_root.authserver, TestRequest())

    def __getattr__(self, name):
        if name.startswith("xmlrpc_"):
            return getattr(self.authserver, name[len("xmlrpc_"):])
        else:
            raise AttributeError("%r has no attribute '%s'" % name)


class InProcessAuthServerFixture(fixtures.Fixture, xmlrpc.XMLRPC):
    """A fixture that runs an in-process authserver."""

    def _setUp(self):
        listener = reactor.listenTCP(0, server.Site(InProcessAuthServer()))
        self.addCleanup(listener.stopListening)
        config.push("in-process-auth-server-fixture", (dedent("""
            [builddmaster]
            authentication_endpoint: http://localhost:%d/
            """) % listener.getHost().port).encode("UTF-8"))
        self.addCleanup(config.pop, "in-process-auth-server-fixture")


class FormatAsRfc3339TestCase(TestCase):

    def test_simple(self):
        t = datetime(2016, 1, 1)
        self.assertEqual('2016-01-01T00:00:00Z', format_as_rfc3339(t))

    def test_microsecond_is_ignored(self):
        ts = datetime(2016, 1, 1, microsecond=10)
        self.assertEqual('2016-01-01T00:00:00Z', format_as_rfc3339(ts))

    def test_tzinfo_is_ignored(self):
        tz = datetime(2016, 1, 1, tzinfo=pytz.timezone('US/Eastern'))
        self.assertEqual('2016-01-01T00:00:00Z', format_as_rfc3339(tz))


class TestSnapBuildBehaviourBase(TestCaseWithFactory):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestSnapBuildBehaviourBase, self).setUp()
        self.pushConfig("snappy", tools_source=None, tools_fingerprint=None)

    def makeJob(self, archive=None, pocket=PackagePublishingPocket.UPDATES,
                **kwargs):
        """Create a sample `ISnapBuildBehaviour`."""
        if archive is None:
            distribution = self.factory.makeDistribution(name="distro")
        else:
            distribution = archive.distribution
        distroseries = self.factory.makeDistroSeries(
            distribution=distribution, name="unstable")
        processor = getUtility(IProcessorSet).getByName("386")
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, architecturetag="i386",
            processor=processor)
        build = self.factory.makeSnapBuild(
            archive=archive, distroarchseries=distroarchseries, pocket=pocket,
            name="test-snap", **kwargs)
        return IBuildFarmJobBehaviour(build)


class TestSnapBuildBehaviour(TestSnapBuildBehaviourBase):
    layer = LaunchpadZopelessLayer

    def test_provides_interface(self):
        # SnapBuildBehaviour provides IBuildFarmJobBehaviour.
        job = SnapBuildBehaviour(None)
        self.assertProvides(job, IBuildFarmJobBehaviour)

    def test_adapts_ISnapBuild(self):
        # IBuildFarmJobBehaviour adapts an ISnapBuild.
        build = self.factory.makeSnapBuild()
        job = IBuildFarmJobBehaviour(build)
        self.assertProvides(job, IBuildFarmJobBehaviour)

    def test_verifyBuildRequest_valid(self):
        # verifyBuildRequest doesn't raise any exceptions when called with a
        # valid builder set.
        job = self.makeJob()
        lfa = self.factory.makeLibraryFileAlias()
        transaction.commit()
        job.build.distro_arch_series.addOrUpdateChroot(lfa)
        builder = MockBuilder()
        job.setBuilder(builder, OkSlave())
        logger = BufferLogger()
        job.verifyBuildRequest(logger)
        self.assertEqual("", logger.getLogBuffer())

    def test_verifyBuildRequest_virtual_mismatch(self):
        # verifyBuildRequest raises on an attempt to build a virtualized
        # build on a non-virtual builder.
        job = self.makeJob()
        lfa = self.factory.makeLibraryFileAlias()
        transaction.commit()
        job.build.distro_arch_series.addOrUpdateChroot(lfa)
        builder = MockBuilder(virtualized=False)
        job.setBuilder(builder, OkSlave())
        logger = BufferLogger()
        e = self.assertRaises(AssertionError, job.verifyBuildRequest, logger)
        self.assertEqual(
            "Attempt to build virtual item on a non-virtual builder.", str(e))

    def test_verifyBuildRequest_archive_disabled(self):
        archive = self.factory.makeArchive(
            enabled=False, displayname="Disabled Archive")
        job = self.makeJob(archive=archive)
        lfa = self.factory.makeLibraryFileAlias()
        transaction.commit()
        job.build.distro_arch_series.addOrUpdateChroot(lfa)
        builder = MockBuilder()
        job.setBuilder(builder, OkSlave())
        logger = BufferLogger()
        e = self.assertRaises(ArchiveDisabled, job.verifyBuildRequest, logger)
        self.assertEqual("Disabled Archive is disabled.", str(e))

    def test_verifyBuildRequest_archive_private_owners_match(self):
        archive = self.factory.makeArchive(private=True)
        job = self.makeJob(
            archive=archive, registrant=archive.owner, owner=archive.owner)
        lfa = self.factory.makeLibraryFileAlias()
        transaction.commit()
        job.build.distro_arch_series.addOrUpdateChroot(lfa)
        builder = MockBuilder()
        job.setBuilder(builder, OkSlave())
        logger = BufferLogger()
        job.verifyBuildRequest(logger)
        self.assertEqual("", logger.getLogBuffer())

    def test_verifyBuildRequest_archive_private_owners_mismatch(self):
        archive = self.factory.makeArchive(private=True)
        job = self.makeJob(archive=archive)
        lfa = self.factory.makeLibraryFileAlias()
        transaction.commit()
        job.build.distro_arch_series.addOrUpdateChroot(lfa)
        builder = MockBuilder()
        job.setBuilder(builder, OkSlave())
        logger = BufferLogger()
        e = self.assertRaises(
            SnapBuildArchiveOwnerMismatch, job.verifyBuildRequest, logger)
        self.assertEqual(
            "Snap package builds against private archives are only allowed "
            "if the snap package owner and the archive owner are equal.",
            str(e))

    def test_verifyBuildRequest_no_chroot(self):
        # verifyBuildRequest raises when the DAS has no chroot.
        job = self.makeJob()
        builder = MockBuilder()
        job.setBuilder(builder, OkSlave())
        logger = BufferLogger()
        e = self.assertRaises(CannotBuild, job.verifyBuildRequest, logger)
        self.assertIn("Missing chroot", str(e))


class TestAsyncSnapBuildBehaviour(TestSnapBuildBehaviourBase):
    run_tests_with = AsynchronousDeferredRunTestForBrokenTwisted.make_factory(
        timeout=10)

    @defer.inlineCallbacks
    def setUp(self):
        super(TestAsyncSnapBuildBehaviour, self).setUp()
        build_username = 'SNAPBUILD-1'
        self.token = {'secret': uuid.uuid4().get_hex(),
                      'username': build_username,
                      'timestamp': datetime.utcnow().isoformat()}
        self.proxy_url = ("http://{username}:{password}"
                          "@{host}:{port}".format(
                              username=self.token['username'],
                              password=self.token['secret'],
                              host=config.snappy.builder_proxy_host,
                              port=config.snappy.builder_proxy_port))
        self.proxy_api = self.useFixture(InProcessProxyAuthAPIFixture())
        yield self.proxy_api.start()
        self.now = time.time()
        self.useFixture(fixtures.MockPatch(
            "time.time", return_value=self.now))

    def makeJob(self, **kwargs):
        # We need a builder slave in these tests, in order that requesting a
        # proxy token can piggyback on its reactor and pool.
        job = super(TestAsyncSnapBuildBehaviour, self).makeJob(**kwargs)
        builder = MockBuilder()
        builder.processor = job.build.processor
        slave = self.useFixture(SlaveTestHelpers()).getClientSlave()
        job.setBuilder(builder, slave)
        self.addCleanup(slave.pool.closeCachedConnections)
        return job

    def getProxyURLMatcher(self, job):
        return AfterPreprocessing(urlsplit, MatchesStructure(
            scheme=Equals("http"),
            username=Equals("{}-{}".format(
                job.build.build_cookie, int(self.now))),
            password=HasLength(32),
            hostname=Equals(config.snappy.builder_proxy_host),
            port=Equals(config.snappy.builder_proxy_port),
            path=Equals("")))

    def getRevocationEndpointMatcher(self, job):
        return Equals("{}/{}-{}".format(
            config.snappy.builder_proxy_auth_api_endpoint,
            job.build.build_cookie, int(self.now)))

    @defer.inlineCallbacks
    def test_composeBuildRequest(self):
        job = self.makeJob()
        lfa = self.factory.makeLibraryFileAlias(db_only=True)
        job.build.distro_arch_series.addOrUpdateChroot(lfa)
        build_request = yield job.composeBuildRequest(None)
        self.assertThat(build_request, MatchesListwise([
            Equals('snap'),
            Equals(job.build.distro_arch_series),
            Equals(job.build.pocket),
            Equals({}),
            IsInstance(dict),
            ]))

    @defer.inlineCallbacks
    def test_requestProxyToken_unconfigured(self):
        self.pushConfig("snappy", builder_proxy_auth_api_admin_secret=None)
        branch = self.factory.makeBranch()
        job = self.makeJob(branch=branch)
        expected_exception_msg = (
            "builder_proxy_auth_api_admin_secret is not configured.")
        with ExpectedException(CannotBuild, expected_exception_msg):
            yield job.extraBuildArgs()

    @defer.inlineCallbacks
    def test_requestProxyToken(self):
        branch = self.factory.makeBranch()
        job = self.makeJob(branch=branch)
        yield job.extraBuildArgs()
        self.assertThat(self.proxy_api.tokens.requests, MatchesListwise([
            MatchesDict({
                "method": Equals("POST"),
                "uri": Equals(urlsplit(
                    config.snappy.builder_proxy_auth_api_endpoint).path),
                "headers": ContainsDict({
                    b"Authorization": MatchesListwise([
                        Equals(b"Basic " + base64.b64encode(
                            b"admin-launchpad.dev:admin-secret"))]),
                    b"Content-Type": MatchesListwise([
                        Equals(b"application/json; charset=UTF-8"),
                        ]),
                    }),
                "content": AfterPreprocessing(json.loads, MatchesDict({
                    "username": StartsWith(job.build.build_cookie + "-"),
                    })),
                }),
            ]))

    @defer.inlineCallbacks
    def test_extraBuildArgs_bzr(self):
        # extraBuildArgs returns appropriate arguments if asked to build a
        # job for a Bazaar branch.
        branch = self.factory.makeBranch()
        job = self.makeJob(branch=branch)
        expected_archives, expected_trusted_keys = (
            yield get_sources_list_for_building(
                job.build, job.build.distro_arch_series, None))
        with dbuser(config.builddmaster.dbuser):
            args = yield job.extraBuildArgs()
        self.assertThat(args, MatchesDict({
            "archive_private": Is(False),
            "archives": Equals(expected_archives),
            "arch_tag": Equals("i386"),
            "branch": Equals(branch.bzr_identity),
            "build_source_tarball": Is(False),
            "build_url": Equals(canonical_url(job.build)),
            "fast_cleanup": Is(True),
            "name": Equals("test-snap"),
            "private": Is(False),
            "proxy_url": self.getProxyURLMatcher(job),
            "revocation_endpoint": self.getRevocationEndpointMatcher(job),
            "series": Equals("unstable"),
            "trusted_keys": Equals(expected_trusted_keys),
            }))

    @defer.inlineCallbacks
    def test_extraBuildArgs_build_request_args(self):
        snap = self.factory.makeSnap()
        request = self.factory.makeSnapBuildRequest(snap=snap)
        job = self.makeJob(snap=snap, build_request=request)
        with dbuser(config.builddmaster.dbuser):
            args = yield job.extraBuildArgs()
        self.assertEqual(request.id, args["build_request_id"])
        expected_timestamp = format_as_rfc3339(request.date_requested)
        self.assertEqual(expected_timestamp, args["build_request_timestamp"])

    @defer.inlineCallbacks
    def test_extraBuildArgs_git(self):
        # extraBuildArgs returns appropriate arguments if asked to build a
        # job for a Git branch.
        [ref] = self.factory.makeGitRefs()
        job = self.makeJob(git_ref=ref)
        expected_archives, expected_trusted_keys = (
            yield get_sources_list_for_building(
                job.build, job.build.distro_arch_series, None))
        with dbuser(config.builddmaster.dbuser):
            args = yield job.extraBuildArgs()
        self.assertThat(args, MatchesDict({
            "archive_private": Is(False),
            "archives": Equals(expected_archives),
            "arch_tag": Equals("i386"),
            "build_source_tarball": Is(False),
            "build_url": Equals(canonical_url(job.build)),
            "fast_cleanup": Is(True),
            "git_repository": Equals(ref.repository.git_https_url),
            "git_path": Equals(ref.name),
            "name": Equals("test-snap"),
            "private": Is(False),
            "proxy_url": self.getProxyURLMatcher(job),
            "revocation_endpoint": self.getRevocationEndpointMatcher(job),
            "series": Equals("unstable"),
            "trusted_keys": Equals(expected_trusted_keys),
            }))

    @defer.inlineCallbacks
    def test_extraBuildArgs_git_HEAD(self):
        # extraBuildArgs returns appropriate arguments if asked to build a
        # job for the default branch in a Launchpad-hosted Git repository.
        [ref] = self.factory.makeGitRefs()
        removeSecurityProxy(ref.repository)._default_branch = ref.path
        job = self.makeJob(git_ref=ref.repository.getRefByPath("HEAD"))
        expected_archives, expected_trusted_keys = (
            yield get_sources_list_for_building(
                job.build, job.build.distro_arch_series, None))
        with dbuser(config.builddmaster.dbuser):
            args = yield job.extraBuildArgs()
        self.assertThat(args, MatchesDict({
            "archive_private": Is(False),
            "archives": Equals(expected_archives),
            "arch_tag": Equals("i386"),
            "build_source_tarball": Is(False),
            "build_url": Equals(canonical_url(job.build)),
            "fast_cleanup": Is(True),
            "git_repository": Equals(ref.repository.git_https_url),
            "name": Equals("test-snap"),
            "private": Is(False),
            "proxy_url": self.getProxyURLMatcher(job),
            "revocation_endpoint": self.getRevocationEndpointMatcher(job),
            "series": Equals("unstable"),
            "trusted_keys": Equals(expected_trusted_keys),
            }))

    @defer.inlineCallbacks
    def test_extraBuildArgs_git_private(self):
        # extraBuildArgs returns appropriate arguments if asked to build a
        # job for a private Git branch.
        self.useFixture(FeatureFixture({SNAP_PRIVATE_FEATURE_FLAG: "on"}))
        self.useFixture(InProcessAuthServerFixture())
        self.pushConfig(
            "launchpad", internal_macaroon_secret_key="some-secret")
        [ref] = self.factory.makeGitRefs(
            information_type=InformationType.USERDATA)
        job = self.makeJob(git_ref=ref, private=True)
        expected_archives, expected_trusted_keys = (
            yield get_sources_list_for_building(
                job.build, job.build.distro_arch_series, None))
        args = yield job.extraBuildArgs()
        split_browse_root = urlsplit(config.codehosting.git_browse_root)
        self.assertThat(args, MatchesDict({
            "archive_private": Is(False),
            "archives": Equals(expected_archives),
            "arch_tag": Equals("i386"),
            "build_source_tarball": Is(False),
            "build_url": Equals(canonical_url(job.build)),
            "fast_cleanup": Is(True),
            "git_repository": AfterPreprocessing(urlsplit, MatchesStructure(
                scheme=Equals(split_browse_root.scheme),
                username=Equals(""),
                password=AfterPreprocessing(
                    Macaroon.deserialize, MatchesStructure(
                        location=Equals(config.vhost.mainsite.hostname),
                        identifier=Equals("snap-build"),
                        caveats=MatchesListwise([
                            MatchesStructure.byEquality(
                                caveat_id="lp.snap-build %s" % job.build.id),
                            ]))),
                hostname=Equals(split_browse_root.hostname),
                port=Equals(split_browse_root.port))),
            "git_path": Equals(ref.name),
            "name": Equals("test-snap"),
            "private": Is(True),
            "proxy_url": self.getProxyURLMatcher(job),
            "revocation_endpoint": self.getRevocationEndpointMatcher(job),
            "series": Equals("unstable"),
            "trusted_keys": Equals(expected_trusted_keys),
            }))

    @defer.inlineCallbacks
    def test_extraBuildArgs_git_url(self):
        # extraBuildArgs returns appropriate arguments if asked to build a
        # job for a Git branch backed by a URL for an external repository.
        url = "https://git.example.org/foo"
        ref = self.factory.makeGitRefRemote(
            repository_url=url, path="refs/heads/master")
        job = self.makeJob(git_ref=ref)
        expected_archives, expected_trusted_keys = (
            yield get_sources_list_for_building(
                job.build, job.build.distro_arch_series, None))
        with dbuser(config.builddmaster.dbuser):
            args = yield job.extraBuildArgs()
        self.assertThat(args, MatchesDict({
            "archive_private": Is(False),
            "archives": Equals(expected_archives),
            "arch_tag": Equals("i386"),
            "build_source_tarball": Is(False),
            "build_url": Equals(canonical_url(job.build)),
            "fast_cleanup": Is(True),
            "git_repository": Equals(url),
            "git_path": Equals("master"),
            "name": Equals("test-snap"),
            "private": Is(False),
            "proxy_url": self.getProxyURLMatcher(job),
            "revocation_endpoint": self.getRevocationEndpointMatcher(job),
            "series": Equals("unstable"),
            "trusted_keys": Equals(expected_trusted_keys),
            }))

    @defer.inlineCallbacks
    def test_extraBuildArgs_git_url_HEAD(self):
        # extraBuildArgs returns appropriate arguments if asked to build a
        # job for the default branch in an external Git repository.
        url = "https://git.example.org/foo"
        ref = self.factory.makeGitRefRemote(repository_url=url, path="HEAD")
        job = self.makeJob(git_ref=ref)
        expected_archives, expected_trusted_keys = (
            yield get_sources_list_for_building(
                job.build, job.build.distro_arch_series, None))
        with dbuser(config.builddmaster.dbuser):
            args = yield job.extraBuildArgs()
        self.assertThat(args, MatchesDict({
            "archive_private": Is(False),
            "archives": Equals(expected_archives),
            "arch_tag": Equals("i386"),
            "build_source_tarball": Is(False),
            "build_url": Equals(canonical_url(job.build)),
            "fast_cleanup": Is(True),
            "git_repository": Equals(url),
            "name": Equals("test-snap"),
            "private": Is(False),
            "proxy_url": self.getProxyURLMatcher(job),
            "revocation_endpoint": self.getRevocationEndpointMatcher(job),
            "series": Equals("unstable"),
            "trusted_keys": Equals(expected_trusted_keys),
            }))

    @defer.inlineCallbacks
    def test_extraBuildArgs_prefers_store_name(self):
        # For the "name" argument, extraBuildArgs prefers Snap.store_name
        # over Snap.name if the former is set.
        job = self.makeJob(store_name="something-else")
        with dbuser(config.builddmaster.dbuser):
            args = yield job.extraBuildArgs()
        self.assertEqual("something-else", args["name"])

    @defer.inlineCallbacks
    def test_extraBuildArgs_archive_trusted_keys(self):
        # If the archive has a signing key, extraBuildArgs sends it.
        yield self.useFixture(InProcessKeyServerFixture()).start()
        archive = self.factory.makeArchive()
        key_path = os.path.join(gpgkeysdir, "ppa-sample@canonical.com.sec")
        yield IArchiveSigningKey(archive).setSigningKey(
            key_path, async_keyserver=True)
        job = self.makeJob(archive=archive)
        self.factory.makeBinaryPackagePublishingHistory(
            distroarchseries=job.build.distro_arch_series,
            pocket=job.build.pocket, archive=archive,
            status=PackagePublishingStatus.PUBLISHED)
        with dbuser(config.builddmaster.dbuser):
            args = yield job.extraBuildArgs()
        self.assertThat(args["trusted_keys"], MatchesListwise([
            Base64KeyMatches("0D57E99656BEFB0897606EE9A022DD1F5001B46D"),
            ]))

    @defer.inlineCallbacks
    def test_extraBuildArgs_channels(self):
        # If the build needs particular channels, extraBuildArgs sends them.
        job = self.makeJob(channels={"snapcraft": "edge"})
        expected_archives, expected_trusted_keys = (
            yield get_sources_list_for_building(
                job.build, job.build.distro_arch_series, None))
        with dbuser(config.builddmaster.dbuser):
            args = yield job.extraBuildArgs()
        self.assertFalse(isProxy(args["channels"]))
        self.assertEqual({"snapcraft": "edge"}, args["channels"])

    @defer.inlineCallbacks
    def test_extraBuildArgs_channels_apt(self):
        # {"snapcraft": "apt"} causes snapcraft to be installed from apt.
        job = self.makeJob(channels={"snapcraft": "apt"})
        expected_archives, expected_trusted_keys = (
            yield get_sources_list_for_building(
                job.build, job.build.distro_arch_series, None))
        with dbuser(config.builddmaster.dbuser):
            args = yield job.extraBuildArgs()
        self.assertNotIn("channels", args)

    @defer.inlineCallbacks
    def test_extraBuildArgs_channels_feature_flag_real_channel(self):
        # If the snap.channels.snapcraft feature flag is set, it identifies
        # the default channel to be used for snapcraft.
        self.useFixture(
            FeatureFixture({SNAP_SNAPCRAFT_CHANNEL_FEATURE_FLAG: "stable"}))
        job = self.makeJob()
        expected_archives, expected_trusted_keys = (
            yield get_sources_list_for_building(
                job.build, job.build.distro_arch_series, None))
        with dbuser(config.builddmaster.dbuser):
            args = yield job.extraBuildArgs()
        self.assertFalse(isProxy(args["channels"]))
        self.assertEqual({"snapcraft": "stable"}, args["channels"])

    @defer.inlineCallbacks
    def test_extraBuildArgs_channels_feature_flag_overridden(self):
        # The snap.channels.snapcraft feature flag can be overridden by
        # explicit configuration.
        self.useFixture(
            FeatureFixture({SNAP_SNAPCRAFT_CHANNEL_FEATURE_FLAG: "stable"}))
        job = self.makeJob(channels={"snapcraft": "apt"})
        expected_archives, expected_trusted_keys = (
            yield get_sources_list_for_building(
                job.build, job.build.distro_arch_series, None))
        with dbuser(config.builddmaster.dbuser):
            args = yield job.extraBuildArgs()
        self.assertNotIn("channels", args)

    @defer.inlineCallbacks
    def test_extraBuildArgs_disallow_internet(self):
        # If external network access is not allowed for the snap,
        # extraBuildArgs does not dispatch a proxy token.
        job = self.makeJob(allow_internet=False)
        with dbuser(config.builddmaster.dbuser):
            args = yield job.extraBuildArgs()
        self.assertNotIn("proxy_url", args)
        self.assertNotIn("revocation_endpoint", args)

    @defer.inlineCallbacks
    def test_extraBuildArgs_build_source_tarball(self):
        # If the snap requests building of a source tarball, extraBuildArgs
        # sends the appropriate arguments.
        job = self.makeJob(build_source_tarball=True)
        with dbuser(config.builddmaster.dbuser):
            args = yield job.extraBuildArgs()
        self.assertTrue(args["build_source_tarball"])

    @defer.inlineCallbacks
    def test_extraBuildArgs_private(self):
        # If the snap is private, extraBuildArgs sends the appropriate
        # arguments.
        self.useFixture(FeatureFixture({SNAP_PRIVATE_FEATURE_FLAG: "on"}))
        job = self.makeJob(private=True)
        with dbuser(config.builddmaster.dbuser):
            args = yield job.extraBuildArgs()
        self.assertTrue(args["private"])

    @defer.inlineCallbacks
    def test_composeBuildRequest_proxy_url_set(self):
        job = self.makeJob()
        build_request = yield job.composeBuildRequest(None)
        self.assertThat(
            build_request[4]["proxy_url"], self.getProxyURLMatcher(job))

    @defer.inlineCallbacks
    def test_composeBuildRequest_deleted(self):
        # If the source branch/repository has been deleted,
        # composeBuildRequest raises CannotBuild.
        branch = self.factory.makeBranch()
        owner = self.factory.makePerson(name="snap-owner")
        job = self.makeJob(registrant=owner, owner=owner, branch=branch)
        branch.destroySelf(break_references=True)
        self.assertIsNone(job.build.snap.branch)
        self.assertIsNone(job.build.snap.git_repository)
        expected_exception_msg = ("Source branch/repository for "
                                  "~snap-owner/test-snap has been deleted.")
        with ExpectedException(CannotBuild, expected_exception_msg):
            yield job.composeBuildRequest(None)

    @defer.inlineCallbacks
    def test_composeBuildRequest_git_ref_deleted(self):
        # If the source Git reference has been deleted, composeBuildRequest
        # raises CannotBuild.
        repository = self.factory.makeGitRepository()
        [ref] = self.factory.makeGitRefs(repository=repository)
        owner = self.factory.makePerson(name="snap-owner")
        job = self.makeJob(registrant=owner, owner=owner, git_ref=ref)
        repository.removeRefs([ref.path])
        self.assertIsNone(job.build.snap.git_ref)
        expected_exception_msg = ("Source branch/repository for "
                                  "~snap-owner/test-snap has been deleted.")
        with ExpectedException(CannotBuild, expected_exception_msg):
            yield job.composeBuildRequest(None)

    @defer.inlineCallbacks
    def test_dispatchBuildToSlave_prefers_lxd(self):
        job = self.makeJob(allow_internet=False)
        builder = MockBuilder()
        builder.processor = job.build.processor
        slave = OkSlave()
        job.setBuilder(builder, slave)
        chroot_lfa = self.factory.makeLibraryFileAlias(db_only=True)
        job.build.distro_arch_series.addOrUpdateChroot(
            chroot_lfa, image_type=BuildBaseImageType.CHROOT)
        lxd_lfa = self.factory.makeLibraryFileAlias(db_only=True)
        job.build.distro_arch_series.addOrUpdateChroot(
            lxd_lfa, image_type=BuildBaseImageType.LXD)
        yield job.dispatchBuildToSlave(DevNullLogger())
        self.assertEqual(
            ('ensurepresent', lxd_lfa.http_url, '', ''), slave.call_log[0])

    @defer.inlineCallbacks
    def test_dispatchBuildToSlave_falls_back_to_chroot(self):
        job = self.makeJob(allow_internet=False)
        builder = MockBuilder()
        builder.processor = job.build.processor
        slave = OkSlave()
        job.setBuilder(builder, slave)
        chroot_lfa = self.factory.makeLibraryFileAlias(db_only=True)
        job.build.distro_arch_series.addOrUpdateChroot(
            chroot_lfa, image_type=BuildBaseImageType.CHROOT)
        yield job.dispatchBuildToSlave(DevNullLogger())
        self.assertEqual(
            ('ensurepresent', chroot_lfa.http_url, '', ''), slave.call_log[0])


class MakeSnapBuildMixin:
    """Provide the common makeBuild method returning a queued build."""

    def makeSnap(self):
        # We can't use self.pushConfig here since this is used in a
        # TrialTestCase instance.
        config_name = self.factory.getUniqueString()
        config.push(config_name, dedent("""
            [snappy]
            store_url: http://sca.example/
            store_upload_url: http://updown.example/
            """))
        self.addCleanup(config.pop, config_name)
        distroseries = self.factory.makeDistroSeries()
        snappyseries = self.factory.makeSnappySeries(
            usable_distro_series=[distroseries])
        return self.factory.makeSnap(
            distroseries=distroseries, store_upload=True,
            store_series=snappyseries,
            store_name=self.factory.getUniqueUnicode(),
            store_secrets={"root": Macaroon().serialize()})

    def makeBuild(self):
        snap = self.makeSnap()
        build = self.factory.makeSnapBuild(
            requester=snap.registrant, snap=snap, status=BuildStatus.BUILDING)
        build.queueBuild()
        return build

    def makeUnmodifiableBuild(self):
        snap = self.makeSnap()
        build = self.factory.makeSnapBuild(
            requester=snap.registrant, snap=snap, status=BuildStatus.BUILDING)
        build.distro_series.status = SeriesStatus.OBSOLETE
        build.queueBuild()
        return build


class TestGetUploadMethodsForSnapBuild(
    MakeSnapBuildMixin, TestGetUploadMethodsMixin, TestCaseWithFactory):
    """IPackageBuild.getUpload-related methods work with Snap builds."""


class TestVerifySuccessfulBuildForSnapBuild(
    MakeSnapBuildMixin, TestVerifySuccessfulBuildMixin, TestCaseWithFactory):
    """IBuildFarmJobBehaviour.verifySuccessfulBuild works."""


class TestHandleStatusForSnapBuild(
    MakeSnapBuildMixin, TestHandleStatusMixin, TrialTestCase,
    fixtures.TestWithFixtures):
    """IPackageBuild.handleStatus works with Snap builds."""
