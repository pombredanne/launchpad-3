# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
# pylint: disable-msg=C0324

"""Test BuildQueue features."""

from datetime import timedelta

from zope.component import getUtility

from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.testing import LaunchpadZopelessLayer

from lp.buildmaster.interfaces.buildfarmjob import BuildFarmJobType
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.interfaces.build import BuildStatus
from lp.soyuz.interfaces.builder import IBuilderSet
from lp.soyuz.model.processor import ProcessorFamilySet
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.model.build import Build
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory


def find_job(test, name, processor='386'):
    """Find build and queue instance for the given source and processor."""
    for build in test.builds:
        if (build.sourcepackagerelease.name == name
            and build.processor.name == processor):
            return (build, build.buildqueue_record)
    return (None, None)


def nth_builder(test, build, n):
    """Find nth builder that can execute the given build."""
    def builder_key(build):
        return (build.processor.id,build.is_virtualized)
    builder = None
    builders = test.builders.get(builder_key(build), [])
    try:
        builder = builders[n-1]
    except IndexError:
        pass
    return builder


def assign_to_builder(test, job_name, builder_number):
    """Simulate assigning a build to a builder."""
    build, bq = find_job(test, job_name)
    builder = nth_builder(test, build, builder_number)
    bq.markAsBuilding(builder)


def print_build_setup(builds):
    """Show the build set-up for a particular test."""
    for build in builds:
        bq = build.buildqueue_record
        spr = build.sourcepackagerelease
        print "%12s, p:%5s, v:%5s e:%s *** s:%5s" % (
            spr.name, build.processor.name, build.is_virtualized,
            bq.estimated_duration, bq.lastscore)


class TestBuildQueueBase(TestCaseWithFactory):
    """Setup the test publisher and some builders."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestBuildQueueBase, self).setUp()
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        # First make nine 'i386' builders.
        self.i1 = self.factory.makeBuilder(name='i386-v-1')
        self.i2 = self.factory.makeBuilder(name='i386-v-2')
        self.i3 = self.factory.makeBuilder(name='i386-v-3')
        self.i4 = self.factory.makeBuilder(name='i386-v-4')
        self.i5 = self.factory.makeBuilder(name='i386-v-5')
        self.i6 = self.factory.makeBuilder(name='i386-n-6', virtualized=False)
        self.i7 = self.factory.makeBuilder(name='i386-n-7', virtualized=False)
        self.i8 = self.factory.makeBuilder(name='i386-n-8', virtualized=False)
        self.i9 = self.factory.makeBuilder(name='i386-n-9', virtualized=False)

        # Next make seven 'hppa' builders.
        processor_fam = ProcessorFamilySet().getByName('hppa')
        proc = processor_fam.processors[0]
        self.h1 = self.factory.makeBuilder(name='hppa-v-1', processor=proc)
        self.h2 = self.factory.makeBuilder(name='hppa-v-2', processor=proc)
        self.h3 = self.factory.makeBuilder(name='hppa-v-3', processor=proc)
        self.h4 = self.factory.makeBuilder(name='hppa-v-4', processor=proc)
        self.h5 = self.factory.makeBuilder(
            name='hppa-n-5', processor=proc, virtualized=False)
        self.h6 = self.factory.makeBuilder(
            name='hppa-n-6', processor=proc, virtualized=False)
        self.h7 = self.factory.makeBuilder(
            name='hppa-n-7', processor=proc, virtualized=False)

        # Finally make five 'amd64' builders.
        processor_fam = ProcessorFamilySet().getByName('amd64')
        proc = processor_fam.processors[0]
        self.a1 = self.factory.makeBuilder(name='amd64-v-1', processor=proc)
        self.a2 = self.factory.makeBuilder(name='amd64-v-2', processor=proc)
        self.a3 = self.factory.makeBuilder(name='amd64-v-3', processor=proc)
        self.a4 = self.factory.makeBuilder(
            name='amd64-n-4', processor=proc, virtualized=False)
        self.a5 = self.factory.makeBuilder(
            name='amd64-n-5', processor=proc, virtualized=False)

        self.builders = dict()
        # x86 native
        self.builders[(1,False)] = [self.i6, self.i7, self.i8, self.i9]
        # x86 virtual
        self.builders[(1,True)] = [
            self.i1, self.i2, self.i3, self.i4, self.i5]

        # amd64 native
        self.builders[(2,True)] = [self.a4, self.a5]
        # amd64 virtual
        self.builders[(2,False)] = [self.a1, self.a2, self.a3]

        # hppa native
        self.builders[(3,True)] = [self.h5, self.h6, self.h7]
        # hppa virtual
        self.builders[(3,False)] = [self.h1, self.h2, self.h3, self.h4]

        # Ensure all builders are operational.
        for builders in self.builders.values():
            for builder in builders:
                builder.builderok = True
                builder.manual = False

        # Disable the sample data builders.
        getUtility(IBuilderSet)['bob'].builderok = False
        getUtility(IBuilderSet)['frog'].builderok = False


class TestBuilderData(TestBuildQueueBase):
    """Test the retrieval of builder related data. The latter is required
    for job dispatch time estimations irrespective of job processor
    architecture and virtualization setting."""

    def setUp(self):
        """Set up some native x86 builds for the test archive."""
        super(TestBuilderData, self).setUp()
        # The builds will be set up as follows:
        #
        #      gedit, p:  386, v:False e:0:01:00 *** s: 1001
        #    firefox, p:  386, v:False e:0:02:00 *** s: 1002
        #        apg, p:  386, v:False e:0:03:00 *** s: 1003
        #        vim, p:  386, v:False e:0:04:00 *** s: 1004
        #        gcc, p:  386, v:False e:0:05:00 *** s: 1005
        #      bison, p:  386, v:False e:0:06:00 *** s: 1006
        #       flex, p:  386, v:False e:0:07:00 *** s: 1007
        #   postgres, p:  386, v:False e:0:08:00 *** s: 1008
        #
        # p=processor, v=virtualized, e=estimated_duration, s=score

        # First mark all builds in the sample data as already built.
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        sample_data = store.find(Build)
        for build in sample_data:
            build.buildstate = BuildStatus.FULLYBUILT
        store.flush()

        # We test builds that target a primary archive.
        self.non_ppa = self.factory.makeArchive(
            name="primary", purpose=ArchivePurpose.PRIMARY)
        self.non_ppa.require_virtualized = False

        self.builds = []
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="gedit", status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa).createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="firefox",
                status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa).createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="apg", status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa).createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="vim", status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa).createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="gcc", status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa).createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="bison", status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa).createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="flex", status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa).createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="postgres",
                status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa).createMissingBuilds())
        # Set up the builds for test.
        score = 1000
        duration = 0
        for build in self.builds:
            score += 1
            duration += 60
            bq = build.buildqueue_record
            bq.lastscore = score
            bq.estimated_duration = timedelta(seconds=duration)
        # print_build_setup(self.builds)

    def test_builder_data(self):
        # Make sure the builder numbers are correct. The builder data will
        # be the same for all of our builds.
        bq = self.builds[0].buildqueue_record
        builder_data = bq._getBuilderData()
        builders_in_total, builders_for_job, builder_stats = builder_data
        self.assertEqual(
            builders_in_total, 21, "The total number of builders is wrong.")
        self.assertEqual(
            builders_for_job, 4,
            "[1] The total number of builders that can build the job in "
            "question is wrong.")
        self.assertEqual(
            builder_stats[(1,False)], 4,
            "The number of native x86 builders is wrong")
        self.assertEqual(
            builder_stats[(1,True)], 5,
            "The number of virtual x86 builders is wrong")
        self.assertEqual(
            builder_stats[(2,False)], 2,
            "The number of native amd64 builders is wrong")
        self.assertEqual(
            builder_stats[(2,True)], 3,
            "The number of virtual amd64 builders is wrong")
        self.assertEqual(
            builder_stats[(3,False)], 3,
            "The number of native hppa builders is wrong")
        self.assertEqual(
            builder_stats[(3,True)], 4,
            "The number of virtual hppa builders is wrong")
        # Disable the native x86 builders.
        for builder in self.builders[(1,False)]:
            builder.builderok = False
        # Get the builder statistics again.
        builder_data = bq._getBuilderData()
        builders_in_total, builders_for_job, builder_stats = builder_data
        # Since all native x86 builders were disabled there are none left
        # to build the job.
        self.assertEqual(
            builders_for_job, 0,
            "[2] The total number of builders that can build the job in "
            "question is wrong.")
        # Re-enable one of them.
        for builder in self.builders[(1,False)]:
            builder.builderok = True
            break
        # Get the builder statistics again.
        builder_data = bq._getBuilderData()
        builders_in_total, builders_for_job, builder_stats = builder_data
        # Now there should be one builder available to build the job.
        self.assertEqual(
            builders_for_job, 1,
            "[3] The total number of builders that can build the job in "
            "question is wrong.")
        # Disable the *virtual* x86 builders -- should not make any
        # difference.
        for builder in self.builders[(1,True)]:
            builder.builderok = False
        # Get the builder statistics again.
        builder_data = bq._getBuilderData()
        builders_in_total, builders_for_job, builder_stats = builder_data
        # There should still be one builder available to build the job.
        self.assertEqual(
            builders_for_job, 1,
            "[4] The total number of builders that can build the job in "
            "question is wrong.")

    def test_free_builder_counts(self):
        # Make sure the builder numbers are correct. The builder data will
        # be the same for all of our builds.
        processor_fam = ProcessorFamilySet().getByName('x86')
        proc_386 = processor_fam.processors[0]
        build = self.builds[0]
        # The build in question is an x86/native one.
        self.assertEqual(build.processor.id, proc_386.id)
        self.assertEqual(build.is_virtualized, False)
        bq = build.buildqueue_record
        builder_data = bq._getBuilderData()
        builders_in_total, builders_for_job, builder_stats = builder_data
        # We have 4 x86 native builders.
        self.assertEqual(
            builder_stats[(proc_386.id,False)], 4,
            "The number of native x86 builders is wrong")
        # Initially all 4 builders are free.
        free_count = bq._freeBuildersCount(
            build.processor, build.is_virtualized)
        self.assertEqual(free_count, 4)
        # Once we assign a build to one of them we should see the free
        # builders count drop by one.
        assign_to_builder(self, 'postgres', 1)
        free_count = bq._freeBuildersCount(
            build.processor, build.is_virtualized)
        self.assertEqual(free_count, 3)
        # When we assign another build to one of them we should see the free
        # builders count drop by one again.
        assign_to_builder(self, 'gcc', 2)
        free_count = bq._freeBuildersCount(
            build.processor, build.is_virtualized)
        self.assertEqual(free_count, 2)
        # Let's use up another builder.
        assign_to_builder(self, 'apg', 3)
        free_count = bq._freeBuildersCount(
            build.processor, build.is_virtualized)
        self.assertEqual(free_count, 1)
        # And now for the last one.
        assign_to_builder(self, 'flex', 4)
        free_count = bq._freeBuildersCount(
            build.processor, build.is_virtualized)
        self.assertEqual(free_count, 0)
        # If we reset the 'flex' build the builder that was assigned to it
        # will be free again.
        build, bq = find_job(self, 'flex')
        bq.reset()
        free_count = bq._freeBuildersCount(
            build.processor, build.is_virtualized)
        self.assertEqual(free_count, 1)


class TestJobClasses(TestCaseWithFactory):
    """Tests covering build farm job type classes."""
    layer = LaunchpadZopelessLayer
    def setUp(self):
        """Set up a native x86 build for the test archive."""
        super(TestJobClasses, self).setUp()

        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        # First mark all builds in the sample data as already built.
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        sample_data = store.find(Build)
        for build in sample_data:
            build.buildstate = BuildStatus.FULLYBUILT
        store.flush()

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
        self.assertEqual(
            bq.specific_job_classes[BuildFarmJobType.PACKAGEBUILD],
            BuildPackageJob)
        self.assertEqual(bq.specific_job.__class__, BuildPackageJob)

    def test_OtherTypeClasses(self):
        """Other job type classes are picked up as well."""
        from zope import component
        from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJob
        class FakeBranchBuild:
            pass

        _build, bq = find_job(self, 'gedit')
        # First make sure that we don't have a job type class registered for
        # 'BRANCHBUILD' yet.
        self.assertTrue(
            bq.specific_job_classes.get(BuildFarmJobType.BRANCHBUILD) is None)

        # Pretend that our `FakeBranchBuild` class implements the
        # `IBuildFarmJob` interface.
        fake_component = FakeBranchBuild()
        component.provideUtility(fake_component, IBuildFarmJob, 'BRANCHBUILD')

        # After pretending that our `FakeBranchBuild` class implements the
        # `IBuildFarmJob` interface for the 'BRANCHBUILD' build farm job type
        # we should see it in the 'specific_job_classes' dictionary.
        self.assertEqual(
            bq.specific_job_classes[BuildFarmJobType.BRANCHBUILD],
            FakeBranchBuild)
