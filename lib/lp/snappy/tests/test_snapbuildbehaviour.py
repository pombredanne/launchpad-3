# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test snap package build behaviour."""

__metaclass__ = type

from datetime import datetime
import uuid

import fixtures
from mock import (
    patch,
    Mock,
    )
import transaction
from testtools import ExpectedException
from testtools.deferredruntest import AsynchronousDeferredRunTest
from testtools.matchers import IsInstance
from twisted.internet import defer
from twisted.trial.unittest import TestCase as TrialTestCase
from zope.component import getUtility

from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.builder import CannotBuild
from lp.buildmaster.interfaces.buildfarmjobbehaviour import (
    IBuildFarmJobBehaviour,
    )
from lp.buildmaster.interfaces.processor import IProcessorSet
from lp.buildmaster.tests.mock_slaves import (
    MockBuilder,
    OkSlave,
    )
from lp.buildmaster.tests.test_buildfarmjobbehaviour import (
    TestGetUploadMethodsMixin,
    TestHandleStatusMixin,
    TestVerifySuccessfulBuildMixin,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.services.config import config
from lp.services.features.testing import FeatureFixture
from lp.services.log.logger import BufferLogger
from lp.snappy.interfaces.snap import (
    SNAP_FEATURE_FLAG,
    SnapBuildArchiveOwnerMismatch,
    )
from lp.snappy.model.snapbuildbehaviour import SnapBuildBehaviour
from lp.soyuz.adapters.archivedependencies import (
    get_sources_list_for_building,
    )
from lp.soyuz.interfaces.archive import ArchiveDisabled
from lp.testing import TestCaseWithFactory
from lp.testing.layers import LaunchpadZopelessLayer


class TestSnapBuildBehaviourBase(TestCaseWithFactory):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestSnapBuildBehaviourBase, self).setUp()
        self.useFixture(FeatureFixture({SNAP_FEATURE_FLAG: u"on"}))
        self.pushConfig("snappy", tools_source=None)

    def makeJob(self, pocket=PackagePublishingPocket.RELEASE, **kwargs):
        """Create a sample `ISnapBuildBehaviour`."""
        distribution = self.factory.makeDistribution(name="distro")
        distroseries = self.factory.makeDistroSeries(
            distribution=distribution, name="unstable")
        processor = getUtility(IProcessorSet).getByName("386")
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, architecturetag="i386",
            processor=processor)
        build = self.factory.makeSnapBuild(
            distroarchseries=distroarchseries, pocket=pocket,
            name=u"test-snap", **kwargs)
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
    run_tests_with = AsynchronousDeferredRunTest

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
        self.revocation_endpoint = "{endpoint}/{username}".format(
            endpoint=config.snappy.builder_proxy_auth_api_endpoint,
            username=build_username)
        self.patcher = patch.object(
            SnapBuildBehaviour, '_requestProxyToken',
            Mock(return_value=self.mockRequestProxyToken())).start()

    def tearDown(self):
        super(TestAsyncSnapBuildBehaviour, self).tearDown()
        self.patcher.stop()

    def mockRequestProxyToken(self):
        return defer.succeed(self.token)

    @defer.inlineCallbacks
    def test_composeBuildRequest(self):
        job = self.makeJob()
        lfa = self.factory.makeLibraryFileAlias(db_only=True)
        job.build.distro_arch_series.addOrUpdateChroot(lfa)
        build_request = yield job.composeBuildRequest(None)
        self.assertEqual(build_request[1], job.build.distro_arch_series)
        self.assertThat(build_request[3], IsInstance(dict))

    @defer.inlineCallbacks
    def test_extraBuildArgs_bzr(self):
        # _extraBuildArgs returns appropriate arguments if asked to build a
        # job for a Bazaar branch.
        branch = self.factory.makeBranch()
        job = self.makeJob(branch=branch)
        expected_archives = get_sources_list_for_building(
            job.build, job.build.distro_arch_series, None)
        args = yield job._extraBuildArgs()
        self.assertEqual({
            "archive_private": False,
            "archives": expected_archives,
            "arch_tag": "i386",
            "branch": branch.bzr_identity,
            "name": u"test-snap",
            "proxy_url": self.proxy_url,
            "revocation_endpoint": self.revocation_endpoint,
            }, args)

    @defer.inlineCallbacks
    def test_extraBuildArgs_git(self):
        # _extraBuildArgs returns appropriate arguments if asked to build a
        # job for a Git branch.
        [ref] = self.factory.makeGitRefs()
        job = self.makeJob(git_ref=ref)
        expected_archives = get_sources_list_for_building(
            job.build, job.build.distro_arch_series, None)
        args = yield job._extraBuildArgs()
        self.assertEqual({
            "archive_private": False,
            "archives": expected_archives,
            "arch_tag": "i386",
            "git_repository": ref.repository.git_https_url,
            "git_path": ref.name,
            "name": u"test-snap",
            "proxy_url": self.proxy_url,
            "revocation_endpoint": self.revocation_endpoint,
            }, args)

    @defer.inlineCallbacks
    def test_extraBuildArgs_proxy_url_set(self):
        job = self.makeJob()
        build_request = yield job.composeBuildRequest(None)
        proxy_url = ("http://{username}:{password}"
                     "@{host}:{port}".format(
                         username=self.token['username'],
                         password=self.token['secret'],
                         host=config.snappy.builder_proxy_host,
                         port=config.snappy.builder_proxy_port))
        self.assertEqual(proxy_url, build_request[3]['proxy_url'])

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


class MakeSnapBuildMixin:
    """Provide the common makeBuild method returning a queued build."""

    def makeBuild(self):
        self.useFixture(FeatureFixture({SNAP_FEATURE_FLAG: u"on"}))
        build = self.factory.makeSnapBuild(status=BuildStatus.BUILDING)
        build.queueBuild()
        return build

    def makeUnmodifiableBuild(self):
        self.useFixture(FeatureFixture({SNAP_FEATURE_FLAG: u"on"}))
        build = self.factory.makeSnapBuild(status=BuildStatus.BUILDING)
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
