# Copyright 2009-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Test BuildQueue features."""

from datetime import timedelta

from storm.sqlobject import SQLObjectNotFound
from storm.store import Store
from zope.security.proxy import removeSecurityProxy

from lp.buildmaster.enums import (
    BuildFarmJobType,
    BuildStatus,
    )
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.services.database.interfaces import IStore
from lp.services.job.model.job import Job
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    )
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
from lp.soyuz.model.buildpackagejob import BuildPackageJob
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
            source = getattr(queue_entry.specific_build, attr, None)
            if source is not None:
                break
        print "%5s, %18s, p:%5s, v:%5s e:%s *** s:%5s" % (
            queue_entry.id, source.name, processor_name(queue_entry),
            queue_entry.virtualized, queue_entry.estimated_duration,
            queue_entry.lastscore)


class TestBuildQueueOldJobDestruction(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_destroy_without_job(self):
        # Newly created BuildQueues won't have an associated Job.
        build = self.factory.makeBinaryPackageBuild()
        bq = build.queueBuild()
        self.assertIs(None, bq.job)
        self.assertIs(
            None, Store.of(build).find(BuildPackageJob, build=build).one())
        bq.destroySelf()
        self.assertIs(None, Store.of(build).find(BuildQueue, id=bq.id).one())

    def test_destroy_with_job(self):
        # Old BuildQueues will have a Job and an IBuildFarmJobOld during
        # the migration. They're all destroyed.
        build = self.factory.makeBinaryPackageBuild()
        bq = removeSecurityProxy(build.queueBuild())
        bfjo = removeSecurityProxy(build).makeJob()
        job = bfjo.job
        bq.job = job
        bq.job_type = BuildFarmJobType.PACKAGEBUILD
        self.assertIsNot(None, bq.specific_old_job)
        self.assertIsNot(None, bq.job)
        bq.destroySelf()
        self.assertIs(None, Store.of(build).find(BuildQueue, id=bq.id).one())
        self.assertIs(None, Store.of(build).find(Job, id=job.id).one())
        self.assertIs(
            None, Store.of(build).find(BuildPackageJob, id=bfjo.id).one())

    def test_destroy_with_dangling_job(self):
        # Old BuildQueues may even have a dangling Job FK between data
        # cleaning and schema dropping. We ignore it and just kill the
        # remaining BuildQueue.
        build = self.factory.makeBinaryPackageBuild()
        bq = removeSecurityProxy(build.queueBuild())
        bq.jobID = 123456
        bq.job_type = BuildFarmJobType.PACKAGEBUILD
        bq.destroySelf()
        self.assertIs(None, Store.of(build).find(BuildQueue, id=bq.id).one())


class TestBuildCancellation(TestCaseWithFactory):
    """Test cases for cancelling builds."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestBuildCancellation, self).setUp()
        self.builder = self.factory.makeBuilder()

    def assertCancelled(self, build, bq):
        self.assertEqual(BuildStatus.CANCELLED, build.status)
        self.assertRaises(SQLObjectNotFound, BuildQueue.get, bq.id)

    def test_binarypackagebuild_cancel(self):
        build = self.factory.makeBinaryPackageBuild()
        bq = build.queueBuild()
        bq.markAsBuilding(self.builder)
        bq.cancel()
        self.assertCancelled(build, bq)

    def test_recipebuild_cancel(self):
        build = self.factory.makeSourcePackageRecipeBuild()
        bq = build.queueBuild()
        bq.markAsBuilding(self.builder)
        bq.cancel()
        self.assertCancelled(build, bq)


class TestBuildQueueDuration(TestCaseWithFactory):
    layer = ZopelessDatabaseLayer

    def _makeBuildQueue(self):
        """Produce a `BuildQueue` object to test."""
        return self.factory.makeSourcePackageRecipeBuild().queueBuild()

    def test_current_build_duration_not_started(self):
        buildqueue = self._makeBuildQueue()
        self.assertEqual(None, buildqueue.current_build_duration)

    def test_current_build_duration(self):
        buildqueue = removeSecurityProxy(self._makeBuildQueue())
        now = buildqueue._now()
        buildqueue._now = FakeMethod(result=now)
        age = timedelta(minutes=3)
        buildqueue.date_started = now - age

        self.assertEqual(age, buildqueue.current_build_duration)


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
        return self.factory.makeSourcePackageRecipeBuild().queueBuild()

    def test_manualScore_prevents_rescoring(self):
        # Manually-set scores are fixed.
        buildqueue = self._makeBuildQueue()
        initial_score = buildqueue.lastscore
        buildqueue.manualScore(initial_score + 5000)
        buildqueue.score()
        self.assertEqual(initial_score + 5000, buildqueue.lastscore)
