# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for BuildFarmJobBehaviorBase."""

from unittest import TestLoader

from zope.component import getUtility

from canonical.testing.layers import ZopelessDatabaseLayer
from lp.testing import TestCaseWithFactory

from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.buildmaster.interfaces.builder import CorruptBuildID
from lp.buildmaster.model.buildfarmjobbehavior import BuildFarmJobBehaviorBase
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.interfaces.processor import IProcessorFamilySet


class FakeBuildFarmJob:
    """Dummy BuildFarmJob."""
    pass


class TestBuildFarmJobBehaviorBase(TestCaseWithFactory):
    """Test very small, basic bits of BuildFarmJobBehaviorBase."""

    layer = ZopelessDatabaseLayer

    def _makeBehavior(self, buildfarmjob=None):
        """Create a `BuildFarmJobBehaviorBase`."""
        if buildfarmjob is None:
            buildfarmjob = FakeBuildFarmJob()
        return BuildFarmJobBehaviorBase(buildfarmjob)

    def _makeBuild(self):
        """Create a `Build` object."""
        x86 = getUtility(IProcessorFamilySet).getByName('x86')
        distroarchseries = self.factory.makeDistroArchSeries(
            architecturetag='x86', processorfamily=x86)
        distroseries = distroarchseries.distroseries
        archive = self.factory.makeArchive(
            distribution=distroseries.distribution)
        pocket = PackagePublishingPocket.RELEASE
        spr = self.factory.makeSourcePackageRelease(
            distroseries=distroseries, archive=archive)

        return spr.createBuild(
            distroarchseries=distroarchseries, pocket=pocket, archive=archive)

    def _makeBuildQueue(self):
        """Create a `BuildQueue` object."""
        return self.factory.makeSourcePackageRecipeBuildJob()

    def test_extractBuildStatus_baseline(self):
        # extractBuildStatus picks the name of the build status out of a
        # dict describing the slave's status.
        slave_status = {'build_status': 'BuildStatus.BUILDING'}
        behavior = self._makeBehavior()
        self.assertEqual(
            BuildStatus.BUILDING.name,
            behavior.extractBuildStatus(slave_status))

    def test_extractBuildStatus_malformed(self):
        # extractBuildStatus errors out when the status string is not
        # of the form it expects.
        slave_status = {'build_status': 'BUILDING'}
        behavior = self._makeBehavior()
        self.assertRaises(
            AssertionError, behavior.extractBuildStatus, slave_status)

    def test_getVerifiedBuild_success(self):
        build = self._makeBuild()
        behavior = self._makeBehavior()
        raw_id = str(build.id)

        self.assertEqual(build, behavior.getVerifiedBuild(raw_id))

    def test_getVerifiedBuild_malformed(self):
        behavior = self._makeBehavior()
        self.assertRaises(CorruptBuildID, behavior.getVerifiedBuild, 'hi!')

    def test_getVerifiedBuild_notfound(self):
        build = self._makeBuild()
        behavior = self._makeBehavior()
        nonexistent_id = str(build.id + 99)

        self.assertRaises(
            CorruptBuildID, behavior.getVerifiedBuild, nonexistent_id)

    def test_getVerifiedBuildQueue_success(self):
        buildqueue = self._makeBuildQueue()
        behavior = self._makeBehavior()
        raw_id = str(buildqueue.id)

        self.assertEqual(buildqueue, behavior.getVerifiedBuildQueue(raw_id))

    def test_getVerifiedBuildQueue_malformed(self):
        behavior = self._makeBehavior()
        self.assertRaises(
            CorruptBuildID, behavior.getVerifiedBuildQueue, 'bye!')

    def test_getVerifiedBuildQueue_notfound(self):
        buildqueue = self._makeBuildQueue()
        behavior = self._makeBehavior()
        nonexistent_id = str(buildqueue.id + 99)

        self.assertRaises(
            CorruptBuildID, behavior.getVerifiedBuildQueue, nonexistent_id)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
