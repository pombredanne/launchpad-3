# Copyright 2014-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test live filesystem build behaviour."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from datetime import datetime
import os.path

import fixtures
import pytz
from testtools.deferredruntest import AsynchronousDeferredRunTest
from testtools.matchers import MatchesListwise
import transaction
from twisted.internet import defer
from twisted.trial.unittest import TestCase as TrialTestCase
from zope.component import getUtility
from zope.security.proxy import Proxy

from lp.archivepublisher.interfaces.archivesigningkey import (
    IArchiveSigningKey,
    )
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
from lp.services.features.testing import FeatureFixture
from lp.services.log.logger import BufferLogger
from lp.soyuz.adapters.archivedependencies import (
    get_sources_list_for_building,
    )
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.interfaces.archive import ArchiveDisabled
from lp.soyuz.interfaces.livefs import (
    LIVEFS_FEATURE_FLAG,
    LiveFSBuildArchiveOwnerMismatch,
    )
from lp.soyuz.model.livefsbuildbehaviour import LiveFSBuildBehaviour
from lp.soyuz.tests.soyuz import Base64KeyMatches
from lp.testing import TestCaseWithFactory
from lp.testing.gpgkeys import gpgkeysdir
from lp.testing.keyserver import InProcessKeyServerFixture
from lp.testing.layers import LaunchpadZopelessLayer


class TestLiveFSBuildBehaviourBase(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestLiveFSBuildBehaviourBase, self).setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: "on"}))

    def makeJob(self, archive=None, pocket=PackagePublishingPocket.RELEASE,
                **kwargs):
        """Create a sample `ILiveFSBuildBehaviour`."""
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
        build = self.factory.makeLiveFSBuild(
            archive=archive, distroarchseries=distroarchseries, pocket=pocket,
            name="test-livefs", **kwargs)
        return IBuildFarmJobBehaviour(build)


class TestLiveFSBuildBehaviour(TestLiveFSBuildBehaviourBase):

    def test_provides_interface(self):
        # LiveFSBuildBehaviour provides IBuildFarmJobBehaviour.
        job = LiveFSBuildBehaviour(None)
        self.assertProvides(job, IBuildFarmJobBehaviour)

    def test_adapts_ILiveFSBuild(self):
        # IBuildFarmJobBehaviour adapts an ILiveFSBuild.
        build = self.factory.makeLiveFSBuild()
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
            LiveFSBuildArchiveOwnerMismatch, job.verifyBuildRequest, logger)
        self.assertEqual(
            "Live filesystem builds against private archives are only allowed "
            "if the live filesystem owner and the archive owner are equal.",
            str(e))

    def test_verifyBuildRequest_no_chroot(self):
        # verifyBuildRequest raises when the DAS has no chroot.
        job = self.makeJob()
        builder = MockBuilder()
        job.setBuilder(builder, OkSlave())
        logger = BufferLogger()
        e = self.assertRaises(CannotBuild, job.verifyBuildRequest, logger)
        self.assertIn("Missing chroot", str(e))


class TestAsyncLiveFSBuildBehaviour(TestLiveFSBuildBehaviourBase):

    run_tests_with = AsynchronousDeferredRunTest.make_factory(timeout=30)

    @defer.inlineCallbacks
    def test_extraBuildArgs(self):
        # _extraBuildArgs returns a reasonable set of additional arguments.
        job = self.makeJob(
            date_created=datetime(2014, 4, 25, 10, 38, 0, tzinfo=pytz.UTC),
            metadata={"project": "distro", "subproject": "special"})
        expected_archives, expected_trusted_keys = (
            yield get_sources_list_for_building(
                job.build, job.build.distro_arch_series, None))
        extra_args = yield job._extraBuildArgs()
        self.assertEqual({
            "archive_private": False,
            "archives": expected_archives,
            "arch_tag": "i386",
            "datestamp": "20140425-103800",
            "pocket": "release",
            "project": "distro",
            "subproject": "special",
            "series": "unstable",
            "trusted_keys": expected_trusted_keys,
            }, extra_args)

    @defer.inlineCallbacks
    def test_extraBuildArgs_proposed(self):
        # _extraBuildArgs returns appropriate arguments if asked to build a
        # job for -proposed.
        job = self.makeJob(
            pocket=PackagePublishingPocket.PROPOSED,
            metadata={"project": "distro"})
        args = yield job._extraBuildArgs()
        self.assertEqual("unstable", args["series"])
        self.assertEqual("proposed", args["pocket"])

    @defer.inlineCallbacks
    def test_extraBuildArgs_no_security_proxy(self):
        # _extraBuildArgs returns an object without security wrapping, even
        # if values in the metadata are (say) lists and hence get proxied by
        # Zope.
        job = self.makeJob(metadata={"lb_args": ["--option=value"]})
        args = yield job._extraBuildArgs()
        self.assertEqual(["--option=value"], args["lb_args"])
        self.assertIsNot(Proxy, type(args["lb_args"]))

    @defer.inlineCallbacks
    def test_extraBuildArgs_archive_trusted_keys(self):
        # If the archive has a signing key, _extraBuildArgs sends it.
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
        args = yield job._extraBuildArgs()
        self.assertThat(args["trusted_keys"], MatchesListwise([
            Base64KeyMatches("0D57E99656BEFB0897606EE9A022DD1F5001B46D"),
            ]))

    @defer.inlineCallbacks
    def test_composeBuildRequest(self):
        job = self.makeJob()
        lfa = self.factory.makeLibraryFileAlias(db_only=True)
        job.build.distro_arch_series.addOrUpdateChroot(lfa)
        build_request = yield job.composeBuildRequest(None)
        args = yield job._extraBuildArgs()
        self.assertEqual(
            ('livefs', job.build.distro_arch_series, {}, args), build_request)


class MakeLiveFSBuildMixin:
    """Provide the common makeBuild method returning a queued build."""

    def makeBuild(self):
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: "on"}))
        build = self.factory.makeLiveFSBuild(status=BuildStatus.BUILDING)
        build.queueBuild()
        return build

    def makeUnmodifiableBuild(self):
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: "on"}))
        build = self.factory.makeLiveFSBuild(status=BuildStatus.BUILDING)
        build.distro_series.status = SeriesStatus.OBSOLETE
        build.queueBuild()
        return build


class TestGetUploadMethodsForLiveFSBuild(
    MakeLiveFSBuildMixin, TestGetUploadMethodsMixin, TestCaseWithFactory):
    """IPackageBuild.getUpload-related methods work with LiveFS builds."""


class TestVerifySuccessfulBuildForLiveFSBuild(
    MakeLiveFSBuildMixin, TestVerifySuccessfulBuildMixin, TestCaseWithFactory):
    """IBuildFarmJobBehaviour.verifySuccessfulBuild works."""


class TestHandleStatusForLiveFSBuild(
    MakeLiveFSBuildMixin, TestHandleStatusMixin, TrialTestCase,
    fixtures.TestWithFixtures):
    """IPackageBuild.handleStatus works with LiveFS builds."""
