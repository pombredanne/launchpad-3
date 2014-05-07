# Copyright 2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test live filesystem build behaviour."""

__metaclass__ = type

from datetime import datetime
from textwrap import dedent

import fixtures
import pytz
from testtools import run_test_with
from testtools.deferredruntest import (
    assert_fails_with,
    AsynchronousDeferredRunTest,
    )
import transaction
from twisted.internet import defer
from twisted.trial.unittest import TestCase as TrialTestCase
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.builder import CannotBuild
from lp.buildmaster.interfaces.buildfarmjobbehaviour import (
    IBuildFarmJobBehaviour,
    )
from lp.buildmaster.tests.mock_slaves import (
    MockBuilder,
    OkSlave,
    )
from lp.buildmaster.tests.test_buildfarmjobbehaviour import (
    TestGetUploadMethodsMixin,
    TestHandleStatusMixin,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.features.testing import FeatureFixture
from lp.services.log.logger import BufferLogger
from lp.soyuz.adapters.archivedependencies import get_sources_list_for_building
from lp.soyuz.interfaces.livefs import LIVEFS_FEATURE_FLAG
from lp.soyuz.interfaces.processor import IProcessorSet
from lp.soyuz.model.livefsbuildbehaviour import LiveFSBuildBehaviour
from lp.testing import TestCaseWithFactory
from lp.testing.layers import LaunchpadZopelessLayer


class TestLiveFSBuildBehaviour(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestLiveFSBuildBehaviour, self).setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: u"on"}))

    def makeJob(self, **kwargs):
        """Create a sample `ILiveFSBuildBehaviour`."""
        distribution = self.factory.makeDistribution(name="distro")
        distroseries = self.factory.makeDistroSeries(
            distribution=distribution, name="unstable")
        processor = getUtility(IProcessorSet).getByName("386")
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, architecturetag="i386",
            processor=processor)
        build = self.factory.makeLiveFSBuild(
            distroarchseries=distroarchseries,
            pocket=PackagePublishingPocket.RELEASE, name=u"livefs", **kwargs)
        return IBuildFarmJobBehaviour(build)

    def test_provides_interface(self):
        # LiveFSBuildBehaviour provides IBuildFarmJobBehaviour.
        job = LiveFSBuildBehaviour(None)
        self.assertProvides(job, IBuildFarmJobBehaviour)

    def test_adapts_ILiveFSBuild(self):
        # IBuildFarmJobBehaviour adapts an ILiveFSBuild.
        build = self.factory.makeLiveFSBuild()
        job = IBuildFarmJobBehaviour(build)
        self.assertProvides(job, IBuildFarmJobBehaviour)

    def test_displayname(self):
        # displayname contains a reasonable description of the job.
        job = self.makeJob()
        self.assertEqual(
            "i386 build of livefs live filesystem in distro unstable RELEASE",
            job.displayname)

    def test_logStartBuild(self):
        # logStartBuild will properly report the image that's being built.
        job = self.makeJob()
        logger = BufferLogger()
        job.logStartBuild(logger)
        self.assertEqual(
            "INFO startBuild(i386 build of livefs live filesystem in distro "
            "unstable RELEASE)\n", logger.getLogBuffer())

    def test_verifyBuildRequest_valid(self):
        # verifyBuildRequest doesn't raise any exceptions when called with a
        # valid builder set.
        job = self.makeJob()
        lfa = self.factory.makeLibraryFileAlias()
        transaction.commit()
        job.build.distroarchseries.addOrUpdateChroot(lfa)
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
        job.build.distroarchseries.addOrUpdateChroot(lfa)
        builder = MockBuilder(virtualized=False)
        job.setBuilder(builder, OkSlave())
        logger = BufferLogger()
        e = self.assertRaises(AssertionError, job.verifyBuildRequest, logger)
        self.assertEqual(
            "Attempt to build virtual item on a non-virtual builder.", str(e))

    def test_verifyBuildRequest_no_chroot(self):
        # verifyBuildRequest raises when the DAS has no chroot.
        job = self.makeJob()
        builder = MockBuilder()
        job.setBuilder(builder, OkSlave())
        logger = BufferLogger()
        e = self.assertRaises(CannotBuild, job.verifyBuildRequest, logger)
        self.assertIn("Missing chroot", str(e))

    def test_getBuildCookie(self):
        # A build cookie is made up of the job type and record id.  The
        # uploadprocessor relies on this format.
        job = self.makeJob()
        cookie = removeSecurityProxy(job).getBuildCookie()
        self.assertEqual("LIVEFSBUILD-%s" % job.build.id, cookie)

    def test_extraBuildArgs(self):
        # _extraBuildArgs returns a reasonable set of additional arguments.
        job = self.makeJob(
            date_created=datetime(2014, 04, 25, 10, 38, 0, tzinfo=pytz.UTC),
            metadata={"project": "distro", "subproject": "special"})
        expected_archives = get_sources_list_for_building(
            job.build, job.build.distroarchseries, None)
        self.assertEqual({
            "archive_private": False,
            "archives": expected_archives,
            "arch_tag": "i386",
            "datestamp": "20140425-103800",
            "project": "distro",
            "subproject": "special",
            "suite": "unstable",
            }, job._extraBuildArgs())

    @run_test_with(AsynchronousDeferredRunTest)
    @defer.inlineCallbacks
    def test_dispatchBuildToSlave(self):
        # dispatchBuildToSlave makes the proper calls to the slave.
        job = self.makeJob()
        lfa = self.factory.makeLibraryFileAlias()
        transaction.commit()
        job.build.distroarchseries.addOrUpdateChroot(lfa)
        slave = OkSlave()
        builder = MockBuilder("bob")
        builder.processor = getUtility(IProcessorSet).getByName("386")
        job.setBuilder(builder, slave)
        logger = BufferLogger()
        yield job.dispatchBuildToSlave("someid", logger)
        self.assertStartsWith(
            logger.getLogBuffer(),
            dedent("""\
                INFO Sending chroot file for live filesystem build to bob
                INFO Initiating build 1-someid on http://fake:0000
                """))
        self.assertEqual(
            ["ensurepresent", "build"], [call[0] for call in slave.call_log])
        build_args = slave.call_log[1][1:]
        self.assertEqual(job.getBuildCookie(), build_args[0])
        self.assertEqual("livefs", build_args[1])
        self.assertEqual([], build_args[3])
        self.assertEqual(job._extraBuildArgs(), build_args[4])

    @run_test_with(AsynchronousDeferredRunTest)
    def test_dispatchBuildToSlave_no_chroot(self):
        # dispatchBuildToSlave fails when the DAS has no chroot.
        job = self.makeJob()
        builder = MockBuilder()
        builder.processor = getUtility(IProcessorSet).getByName("386")
        job.setBuilder(builder, OkSlave())
        d = job.dispatchBuildToSlave("someid", BufferLogger())
        return assert_fails_with(d, CannotBuild)


class MakeLiveFSBuildMixin:
    """Provide the common makeBuild method returning a queued build."""

    def makeBuild(self):
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: u"on"}))
        build = self.factory.makeLiveFSBuild(status=BuildStatus.BUILDING)
        build.queueBuild()
        return build


class TestGetUploadMethodsForLiveFSBuild(
    MakeLiveFSBuildMixin, TestGetUploadMethodsMixin, TestCaseWithFactory):
    """IPackageBuild.getUpload-related methods work with LiveFS builds."""


class TestHandleStatusForLiveFSBuild(
    MakeLiveFSBuildMixin, TestHandleStatusMixin, TrialTestCase,
    fixtures.TestWithFixtures):
    """IPackageBuild.handleStatus works with LiveFS builds."""
