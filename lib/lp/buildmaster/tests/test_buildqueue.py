# Copyright 2009-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Test BuildQueue features."""

from datetime import timedelta

from storm.sqlobject import SQLObjectNotFound
from storm.store import Store
from zope import component
from zope.component import getGlobalSiteManager

from lp.buildmaster.enums import (
    BuildFarmJobType,
    BuildStatus,
    )
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJob
from lp.buildmaster.model.buildfarmjob import BuildFarmJobMixin
from lp.buildmaster.model.buildqueue import (
    BuildQueue,
    specific_job_classes,
    )
from lp.services.database.interfaces import IStore
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    )
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory
from lp.testing.fakemethod import FakeMethod
from lp.testing.layers import (
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )


def find_job(test, name, processor='386'):
    """Find build and queue instance for the given source and processor."""

    def processor_matches(bq):
        if processor is None:
            return (bq.processor is None)
        else:
            return (processor == bq.processor.name)

    for build in test.builds:
        bq = build.buildqueue_record
        source = None
        for attr in ('source_package_release', 'recipe'):
            source = getattr(build, attr, None)
            if source is not None:
                break
        if (source.name == name and processor_matches(bq)):
            return (build, bq)
    return (None, None)


def print_build_setup(builds):
    """Show the build set-up for a particular test."""

    def processor_name(bq):
        return ('None' if bq.processor is None else bq.processor.name)

    print ""
    queue_entries = [build.buildqueue_record for build in builds]
    queue_entries = sorted(
        queue_entries, key=lambda qe: qe.job.id, reverse=True)
    queue_entries = sorted(queue_entries, key=lambda qe: qe.lastscore)
    for queue_entry in queue_entries:
        source = None
        for attr in ('sourcepackagerelease', 'sourcepackagename'):
            source = getattr(queue_entry.specific_job.build, attr, None)
            if source is not None:
                break
        print "%5s, %18s, p:%5s, v:%5s e:%s *** s:%5s" % (
            queue_entry.id, source.name, processor_name(queue_entry),
            queue_entry.virtualized, queue_entry.estimated_duration,
            queue_entry.lastscore)


class TestBuildCancellation(TestCaseWithFactory):
    """Test cases for cancelling builds."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestBuildCancellation, self).setUp()
        self.builder = self.factory.makeBuilder()

    def _makeBuildQueue(self, bfj, job):
        return BuildQueue(
            build_farm_job=bfj.build_farm_job, job=job, lastscore=9999,
            job_type=BuildFarmJobType.PACKAGEBUILD,
            estimated_duration=timedelta(seconds=69), virtualized=True)

    def assertCancelled(self, build, buildqueue):
        self.assertEqual(BuildStatus.CANCELLED, build.status)
        self.assertIs(None, buildqueue.specific_job)
        self.assertRaises(SQLObjectNotFound, BuildQueue.get, buildqueue.id)

    def test_binarypackagebuild_cancel(self):
        build = self.factory.makeBinaryPackageBuild()
        buildpackagejob = build.makeJob()
        bq = self._makeBuildQueue(build, buildpackagejob.job)
        Store.of(build).add(bq)
        bq.markAsBuilding(self.builder)
        bq.cancel()

        self.assertCancelled(buildpackagejob.build, bq)

    def test_recipebuild_cancel(self):
        bq = self.factory.makeSourcePackageRecipeBuildJob()
        build = bq.specific_job.build
        bq.markAsBuilding(self.builder)
        bq.cancel()

        self.assertCancelled(build, bq)


class TestBuildQueueDuration(TestCaseWithFactory):
    layer = ZopelessDatabaseLayer

    def _makeBuildQueue(self):
        """Produce a `BuildQueue` object to test."""
        return self.factory.makeSourcePackageRecipeBuildJob()

    def test_current_build_duration_not_started(self):
        buildqueue = self._makeBuildQueue()
        self.assertEqual(None, buildqueue.current_build_duration)

    def test_current_build_duration(self):
        buildqueue = self._makeBuildQueue()
        now = buildqueue._now()
        buildqueue._now = FakeMethod(result=now)
        age = timedelta(minutes=3)
        buildqueue.job.date_started = now - age

        self.assertEqual(age, buildqueue.current_build_duration)


class TestJobClasses(TestCaseWithFactory):
    """Tests covering build farm job type classes."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Set up a native x86 build for the test archive."""
        super(TestJobClasses, self).setUp()

        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        # First mark all builds in the sample data as already built.
        sample_data = IStore(BinaryPackageBuild).find(BinaryPackageBuild)
        for build in sample_data:
            build.buildstate = BuildStatus.FULLYBUILT
        IStore(BinaryPackageBuild).flush()

        # We test builds that target a primary archive.
        self.non_ppa = self.factory.makeArchive(
            name="primary", purpose=ArchivePurpose.PRIMARY)
        self.non_ppa.require_virtualized = False

        self.builds = []
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="gedit", status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa).createMissingBuilds())

    def test_BuildPackageJob(self):
        """`BuildPackageJob` is one of the job type classes."""
        from lp.soyuz.model.buildpackagejob import BuildPackageJob
        _build, bq = find_job(self, 'gedit')

        # This is a binary package build.
        self.assertEqual(
            BuildFarmJobType.PACKAGEBUILD, bq.job_type,
            "This is a binary package build")

        # The class registered for 'PACKAGEBUILD' is `BuildPackageJob`.
        self.assertEqual(
            BuildPackageJob,
            specific_job_classes()[BuildFarmJobType.PACKAGEBUILD],
            "The class registered for 'PACKAGEBUILD' is `BuildPackageJob`")

        # The 'specific_job' object associated with this `BuildQueue`
        # instance is of type `BuildPackageJob`.
        self.assertTrue(bq.specific_job is not None)
        self.assertEqual(
            BuildPackageJob, bq.specific_job.__class__,
            "The 'specific_job' object associated with this `BuildQueue` "
            "instance is of type `BuildPackageJob`")

    def test_OtherTypeClasses(self):
        """Other job type classes are picked up as well."""

        class FakeBranchBuild(BuildFarmJobMixin):
            pass

        _build, bq = find_job(self, 'gedit')
        # First make sure that we don't have a job type class registered for
        # 'BRANCHBUILD' yet.
        self.assertTrue(
            specific_job_classes().get(BuildFarmJobType.BRANCHBUILD) is None)

        try:
            # Pretend that our `FakeBranchBuild` class implements the
            # `IBuildFarmJob` interface.
            component.provideUtility(
                FakeBranchBuild, IBuildFarmJob, 'BRANCHBUILD')

            # Now we should see the `FakeBranchBuild` class "registered"
            # in the `specific_job_classes` dictionary under the
            # 'BRANCHBUILD' key.
            self.assertEqual(
                specific_job_classes()[BuildFarmJobType.BRANCHBUILD],
                FakeBranchBuild)
        finally:
            # Just de-register the utility so we don't affect other
            # tests.
            site_manager = getGlobalSiteManager()
            site_manager.unregisterUtility(
                FakeBranchBuild, IBuildFarmJob, 'BRANCHBUILD')


class TestPlatformData(TestCaseWithFactory):
    """Tests covering the processor/virtualized properties."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Set up a native x86 build for the test archive."""
        super(TestPlatformData, self).setUp()

        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        # First mark all builds in the sample data as already built.
        sample_data = IStore(BinaryPackageBuild).find(BinaryPackageBuild)
        for build in sample_data:
            build.buildstate = BuildStatus.FULLYBUILT
        IStore(BinaryPackageBuild).flush()

        # We test builds that target a primary archive.
        self.non_ppa = self.factory.makeArchive(
            name="primary", purpose=ArchivePurpose.PRIMARY)
        self.non_ppa.require_virtualized = False

        self.builds = []
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="gedit", status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa).createMissingBuilds())

    def test_JobPlatformSettings(self):
        """The `BuildQueue` instance shares the processor/virtualized
        properties with the associated `Build`."""
        build, bq = find_job(self, 'gedit')

        # Make sure the 'processor' properties are the same.
        self.assertEqual(
            bq.processor, build.processor,
            "The 'processor' property deviates.")

        # Make sure the 'virtualized' properties are the same.
        self.assertEqual(
            bq.virtualized, build.is_virtualized,
            "The 'virtualized' property deviates.")


class TestBuildQueueManual(TestCaseWithFactory):
    layer = ZopelessDatabaseLayer

    def _makeBuildQueue(self):
        """Produce a `BuildQueue` object to test."""
        return self.factory.makeSourcePackageRecipeBuildJob()

    def test_manualScore_prevents_rescoring(self):
        # Manually-set scores are fixed.
        buildqueue = self._makeBuildQueue()
        initial_score = buildqueue.lastscore
        buildqueue.manualScore(initial_score + 5000)
        buildqueue.score()
        self.assertEqual(initial_score + 5000, buildqueue.lastscore)
