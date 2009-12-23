# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test BuildQueue features."""

import unittest

from datetime import datetime, timedelta
from pytz import utc

from zope.component import getUtility

from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.testing import LaunchpadZopelessLayer

from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.interfaces.build import BuildStatus, IBuildSet
from lp.soyuz.interfaces.builder import IBuilderSet
from lp.soyuz.model.processor import ProcessorFamilySet
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.model.build import Build
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory


def almost_equal(a, b, deviation=1):
    # Compare the values tolerating the given deviation. This used to
    # avoid spurious failures in time based tests.
    if abs(a - b) <= deviation:
        return True
    else:
        return False

def find_job(test, name, processor='386'):
    result = None
    for build in test.builds:
        if (build.sourcepackagerelease.name == name
            and build.processor.name == processor):
            result = build
            break
    if result is not None:
        return (result, result.buildqueue_record)
    else:
        return (None, None)

def builder_key(build):
    return (build.processor.id,build.is_virtualized)

def nth_builder(test, build, n):
    builder = None
    builders = test.builders.get(builder_key(build), [])
    try:
        builder = builders[n-1]
    except IndexError:
        pass
    return builder

def assign_to_builder(test, job_name, builder_number):
    build, bq = find_job(test, job_name)
    builder = nth_builder(test, build, builder_number)
    bq.markAsBuilding(builder)

def check_mintime_to_builder(test, build, bq, free_builders, min_time):
    builders = bq._freeBuildersCount(*builder_key(build))
    delay = bq._minTimeToNextBuilderAvailable(False)
    test.assertEqual(builders, free_builders, "Wrong number of free builders")
    test.assertTrue(
        almost_equal(delay, min_time),
        "Wrong min time to next available builder (%s != %s)"
        % (delay, min_time))

def set_remaining_time_for_running_job(bq, remainder):
    offset = bq.estimated_duration.seconds - remainder
    bq.setDateStarted(
        datetime.utcnow().replace(tzinfo=utc) - timedelta(seconds=offset))

def check_job_delay_estimate(test, build, bq, expected_delay):
    now = datetime.utcnow()
    estimate = bq.getEstimatedJobStartTime()
    estimate -= now
    estimate = estimate.seconds
    test.assertTrue(
        almost_equal(estimate, expected_delay),
        "Expected (%s) and estimated delay (%s) for %s do not match"
         % (expected_delay, estimate, build.sourcepackagerelease.name))


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


class TestDispatchPrimarySingleArchAndJobtype(TestBuildQueueBase):
    """Test dispatch time estimates for binary builds (i.e. single build
    farm job type) targetting a single processor architecture and the primary
    archive.
    """
    def setUp(self):
        """Set up some native x86 builds for the test archive."""
        super(TestDispatchPrimarySingleArchAndJobtype, self).setUp()
        # The builds will be set up as follows:
        #
        #    postgres, p:  386, v:False e:0:10:00 *** s: 1010
        #        flex, p:  386, v:False e:0:09:00 *** s: 1009
        #       bison, p:  386, v:False e:0:08:00 *** s: 1008
        #         gcc, p:  386, v:False e:0:07:00 *** s: 1007
        #         vim, p:  386, v:False e:0:06:00 *** s: 1006
        #         apg, p:  386, v:False e:0:05:00 *** s: 1005
        #thunderpants, p:  386, v:False e:0:04:00 *** s: 1004
        #    cobblers, p:  386, v:False e:0:03:00 *** s: 1003
        #     firefox, p:  386, v:False e:0:02:00 *** s: 1002
        #       gedit, p:  386, v:False e:0:01:00 *** s: 1001
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
                sourcename="firefox", status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa).createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="cobblers",
                status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa).createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="thunderpants",
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

    def test_all_jobs_pending(self):
        # Test basic dispatch estimation: all jobs target a single
        # processor/virtualization combination, all jobs are pending.
        expected_delays = dict(
            postgres=0,
            flex=600,
            bison=570,
            gcc=540,
            vim=510,
            # We only have native i386 builders, that's why the estimated
            # dispatch delays for the jobs that follow are increasing again.
            apg=600,
            thunderpants=675,
            cobblers=735,
            firefox=780,
            gedit=810)

        actual_delays = dict()

        # Get estimated dispatch times.
        for index, build in enumerate(reversed(self.builds)):
            bq = build.buildqueue_record
            spr = build.sourcepackagerelease
            now = datetime.utcnow()
            estimate = bq.getEstimatedJobStartTime()
            estimate -= now
            actual_delays[spr.name] = estimate.seconds

        for source, delay in actual_delays.iteritems():
            expected = expected_delays[source]
            # Are the delays computed the same as the ones expected?
            # Allow for a deviation of up two 2 seconds to avoid spurious
            # test failures.
            self.assertTrue(
                almost_equal(expected, delay),
                "Expected (%s) and actual delay (%s) for %s do not match"
                 % (expected, delay, source))

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

    def test_no_builders_available(self):
        # We cannot estimate the dispatch time for a job of interest (JOI)
        # if there is no builder that can build it.
        bq = self.builds[0].buildqueue_record
        # Disable the builders that can build this job.
        builders = self.builders.get((1, False), [])
        for builder in builders:
            builder.builderok = False
        builder_data = bq._getBuilderData()
        builders_in_total, builders_for_job, builder_stats = builder_data
        self.assertEqual(
            builders_for_job, 0,
            "[1] The total number of builders that can build the job in "
            "question is wrong.")
        self.assertTrue(
            bq.getEstimatedJobStartTime() is None,
            "No builders for job available -> no dispatch estimate.")

    def test_min_time_to_next_builder(self):
        # Test the estimation of the minimum time until a builder becomes
        # available.

        # The builds are set up as follows:
        #
        #    postgres, p:  386, v:False e:0:10:00 *** s: 1010
        #        flex, p:  386, v:False e:0:09:00 *** s: 1009
        #       bison, p:  386, v:False e:0:08:00 *** s: 1008
        #         gcc, p:  386, v:False e:0:07:00 *** s: 1007
        #         vim, p:  386, v:False e:0:06:00 *** s: 1006
        #         apg, p:  386, v:False e:0:05:00 *** s: 1005
        #thunderpants, p:  386, v:False e:0:04:00 *** s: 1004
        #    cobblers, p:  386, v:False e:0:03:00 *** s: 1003
        #     firefox, p:  386, v:False e:0:02:00 *** s: 1002
        #       gedit, p:  386, v:False e:0:01:00 *** s: 1001
        #
        # p=processor, v=virtualized, e=estimated_duration, s=score

        apg_build, apg_job = find_job(self, 'apg')
        check_mintime_to_builder(self, apg_build, apg_job, 4, 0)

        # Assign the postgres job to a builder.
        assign_to_builder(self, 'postgres', 1)
        # Now one builder is gone. But there should still be a builder
        # immediately available.
        check_mintime_to_builder(self, apg_build, apg_job, 3, 0)

        assign_to_builder(self, 'flex', 2)
        check_mintime_to_builder(self, apg_build, apg_job, 2, 0)

        assign_to_builder(self, 'bison', 3)
        check_mintime_to_builder(self, apg_build, apg_job, 1, 0)

        assign_to_builder(self, 'gcc', 4)
        # Now that no builder is immediately available, the shortest
        # remaing build time (based on the estimated duration) is returned:
        #   420 seconds 
        # This is equivalent to the 'gcc' job's estimated duration.
        check_mintime_to_builder(self, apg_build, apg_job, 0, 420)

        # Now we pretend that the 'postgres' started 5 minutes ago. Its
        # remaining execution time should be 5 minutes = 300 seconds and
        # it now becomes the job whose builder becomes available next.
        build, bq = find_job(self, 'postgres')
        set_remaining_time_for_running_job(bq, 300)
        check_mintime_to_builder(self, apg_build, apg_job, 0, 300)

        # What happens when jobs overdraw the estimated duration? Let's
        # pretend the 'flex' job started 10 minutes ago.
        build, bq = find_job(self, 'flex')
        set_remaining_time_for_running_job(bq, -60)
        # In such a case we assume that the job will complete within 2
        # minutes, this is a guess that has worked well so far.
        check_mintime_to_builder(self, apg_build, apg_job, 0, 120)

        # If there's a job that will complete within a shorter time then
        # we expect to be given that time frame.
        build, bq = find_job(self, 'postgres')
        set_remaining_time_for_running_job(bq, 30)
        check_mintime_to_builder(self, apg_build, apg_job, 0, 30)

        # The delay for 'apg' is as follows:
        #   - 6 minutes (360 seconds) estimated duration for 'vim' which
        #     is ahead of 'apg' in the queue.
        #   - half a minute (30 seconds) until the next builder becomes
        #     available
        #   TOTAL : 390 seconds
        check_job_delay_estimate(self, apg_build, apg_job, 390)


class TestDispatchPrimaryMultiArchSingleJobtype(TestBuildQueueBase):
    """Test dispatch time estimates for binary builds (i.e. single build
    farm job type) targetting a single processor architecture and the primary
    archive.
    """
    def setUp(self):
        """Set up some native x86 builds for the test archive."""
        super(TestDispatchPrimaryMultiArchSingleJobtype, self).setUp()
        # The builds will be set up as follows:
        #
        #       gedit, p: hppa, v:False e:0:01:00 *** s: 1001
        #       gedit, p:  386, v:False e:0:02:00 *** s: 1002
        #     firefox, p: hppa, v:False e:0:03:00 *** s: 1003
        #     firefox, p:  386, v:False e:0:04:00 *** s: 1004
        #    cobblers, p: hppa, v:False e:0:05:00 *** s: 1005
        #    cobblers, p:  386, v:False e:0:06:00 *** s: 1006
        #thunderpants, p: hppa, v:False e:0:07:00 *** s: 1007
        #thunderpants, p:  386, v:False e:0:08:00 *** s: 1008
        #         apg, p: hppa, v:False e:0:09:00 *** s: 1009
        #         apg, p:  386, v:False e:0:10:00 *** s: 1010
        #         vim, p: hppa, v:False e:0:11:00 *** s: 1011
        #         vim, p:  386, v:False e:0:12:00 *** s: 1012
        #         gcc, p: hppa, v:False e:0:13:00 *** s: 1013
        #         gcc, p:  386, v:False e:0:14:00 *** s: 1014
        #       bison, p: hppa, v:False e:0:15:00 *** s: 1015
        #       bison, p:  386, v:False e:0:16:00 *** s: 1016
        #        flex, p: hppa, v:False e:0:17:00 *** s: 1017
        #        flex, p:  386, v:False e:0:18:00 *** s: 1018
        #    postgres, p: hppa, v:False e:0:19:00 *** s: 1019
        #    postgres, p:  386, v:False e:0:20:00 *** s: 1020
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
                archive=self.non_ppa,
                architecturehintlist='any').createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="firefox", status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa,
                architecturehintlist='any').createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="cobblers", status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa,
                architecturehintlist='any').createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="thunderpants",
                status=PackagePublishingStatus.PUBLISHED, archive=self.non_ppa,
                architecturehintlist='any').createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="apg", status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa,
                architecturehintlist='any').createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="vim", status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa,
                architecturehintlist='any').createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="gcc", status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa,
                architecturehintlist='any').createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="bison", status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa,
                architecturehintlist='any').createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="flex", status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa,
                architecturehintlist='any').createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="postgres",
                status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa,
                architecturehintlist='any').createMissingBuilds())
        # Set up the builds for test.
        score = 1000
        duration = 0
        for build in self.builds:
            score += 1
            duration += 60
            bq = build.buildqueue_record
            bq.lastscore = score
            bq.estimated_duration = timedelta(seconds=duration)

    def test_2(self):
        pass
