# Copyright 2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test live filesystem build features."""

__metaclass__ = type

from datetime import timedelta

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.app.errors import NotFoundError
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.buildqueue import IBuildQueue
from lp.buildmaster.interfaces.packagebuild import IPackageBuild
from lp.services.database.interfaces import IStore
from lp.services.features.testing import FeatureFixture
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.interfaces.livefs import (
    LIVEFS_FEATURE_FLAG,
    LiveFSFeatureDisabled,
    )
from lp.soyuz.interfaces.livefsbuild import (
    ILiveFSBuild,
    ILiveFSBuildSet,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.layers import LaunchpadZopelessLayer
from lp.testing.mail_helpers import pop_notifications


class TestLiveFSBuildFeatureFlag(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_feature_flag_disabled(self):
        # Without a feature flag, we will not create new LiveFSBuilds.
        self.assertRaises(
            LiveFSFeatureDisabled, getUtility(ILiveFSBuildSet).new,
            None, None, self.factory.makeArchive(),
            self.factory.makeDistroArchSeries(), None, None, None)


class TestLiveFSBuild(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestLiveFSBuild, self).setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: u"on"}))
        self.build = self.factory.makeLiveFSBuild()

    def test_implements_interfaces(self):
        # LiveFSBuild implements IPackageBuild and ILiveFSBuild.
        self.assertProvides(self.build, IPackageBuild)
        self.assertProvides(self.build, ILiveFSBuild)

    def test_queueBuild(self):
        # LiveFSBuild can create the queue entry for itself.
        bq = self.build.queueBuild()
        self.assertProvides(bq, IBuildQueue)
        self.assertEqual(
            self.build.build_farm_job, removeSecurityProxy(bq)._build_farm_job)
        self.assertEqual(self.build, bq.specific_build)
        self.assertEqual(self.build.virtualized, bq.virtualized)
        self.assertIsNotNone(bq.processor)
        self.assertEqual(bq, self.build.buildqueue_record)

    def test_current_component_primary(self):
        # LiveFSBuilds for primary archives always build in universe for the
        # time being.
        self.assertEqual(ArchivePurpose.PRIMARY, self.build.archive.purpose)
        self.assertEqual("universe", self.build.current_component.name)

    def test_current_component_ppa(self):
        # PPAs only have indices for main, so LiveFSBuilds for PPAs always
        # build in main.
        build = self.factory.makeLiveFSBuild(
            archive=self.factory.makeArchive())
        self.assertEqual("main", build.current_component.name)

    def test_is_private(self):
        # A LiveFSBuild is private iff its owner is.
        self.assertFalse(self.build.is_private)
        # TODO archive too?  need to override PackageBuild.is_private in
        # LiveFSBuild?

    def test_can_be_cancelled(self):
        # For all states that can be cancelled, can_be_cancelled returns True.
        ok_cases = [
            BuildStatus.BUILDING,
            BuildStatus.NEEDSBUILD,
            ]
        for status in BuildStatus:
            if status in ok_cases:
                self.assertTrue(self.build.can_be_cancelled)
            else:
                self.assertFalse(self.build.can_be_cancelled)

    def test_cancel_not_in_progress(self):
        # The cancel() method for a pending build leaves it in the CANCELLED
        # state.
        self.build.queueBuild()
        self.build.cancel()
        self.assertEqual(BuildStatus.CANCELLED, self.build.status)
        self.assertIsNone(self.build.buildqueue_record)

    def test_cancel_in_progress(self):
        # The cancel() method for a building build leaves it in the
        # CANCELLING state.
        bq = self.build.queueBuild()
        bq.markAsBuilding(self.factory.makeBuilder())
        self.build.cancel()
        self.assertEqual(BuildStatus.CANCELLING, self.build.status)
        self.assertEqual(bq, self.build.buildqueue_record)

    def test_estimateDuration(self):
        # Without previous builds, the default time estimate is 30m.
        self.assertEqual(1800, self.build.estimateDuration().seconds)

    def test_estimateDuration_with_history(self):
        # Previous builds of the same live filesystem are used for estimates.
        self.factory.makeLiveFSBuild(
            requester=self.build.requester, livefs=self.build.livefs,
            distroarchseries=self.build.distroarchseries,
            status=BuildStatus.FULLYBUILT, duration=timedelta(seconds=335))
        self.assertEqual(335, self.build.estimateDuration().seconds)

    def test_getFileByName(self):
        # getFileByName returns the logs when requested by name.
        self.build.setLog(
            self.factory.makeLibraryFileAlias(filename="buildlog.txt.gz"))
        self.assertEqual(
            self.build.log, self.build.getFileByName("buildlog.txt.gz"))
        self.assertRaises(NotFoundError, self.build.getFileByName, "foo")
        self.build.storeUploadLog("uploaded")
        self.assertEqual(
            self.build.upload_log,
            self.build.getFileByName(self.build.upload_log.filename))

    # TODO getFileByName on other files

    def test_notify_fullybuilt(self):
        # notify does not send mail when a LiveFSBuild completes normally.
        person = self.factory.makePerson(name="person")
        build = self.factory.makeLiveFSBuild(requester=person)
        build.updateStatus(BuildStatus.FULLYBUILT)
        IStore(build).flush()
        build.notify()
        self.assertEqual(0, len(pop_notifications()))

    # TODO real notification

    def addFakeBuildLog(self, build):
        build.setLog(self.factory.makeLibraryFileAlias("mybuildlog.txt"))

    def test_log_url(self):
        # The log URL for a live filesystem build will use the archive context.
        self.addFakeBuildLog(self.build)
        self.assertEqual(
            "http://launchpad.dev/%s/+archive/primary/+livefsbuild/%d/+files/"
            "mybuildlog.txt" % (
                self.build.distribution.name, self.build.build_farm_job.id),
            self.build.log_url)


class TestLiveFSBuildSet(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestLiveFSBuildSet, self).setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: u"on"}))

    def test_getByBuildFarmJob_works(self):
        build = self.factory.makeLiveFSBuild()
        self.assertEqual(
            build,
            getUtility(ILiveFSBuildSet).getByBuildFarmJob(
                build.build_farm_job))

    def test_getByBuildFarmJob_returns_None_when_missing(self):
        bpb = self.factory.makeBinaryPackageBuild()
        self.assertIsNone(
            getUtility(ILiveFSBuildSet).getByBuildFarmJob(bpb.build_farm_job))

    def test_getByBuildFarmJobs_works(self):
        builds = [self.factory.makeLiveFSBuild() for i in range(10)]
        self.assertContentEqual(
            builds,
            getUtility(ILiveFSBuildSet).getByBuildFarmJobs(
                [build.build_farm_job for build in builds]))

    def test_getByBuildFarmJobs_works_empty(self):
        self.assertContentEqual(
            [], getUtility(ILiveFSBuildSet).getByBuildFarmJobs([]))
