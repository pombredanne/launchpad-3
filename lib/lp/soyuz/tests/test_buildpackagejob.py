# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test BuildQueue features."""

from datetime import timedelta

from zope.component import getUtility

from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.testing import LaunchpadZopelessLayer

from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.interfaces.build import BuildStatus
from lp.soyuz.interfaces.builder import IBuilderSet
from lp.soyuz.model.processor import ProcessorFamilySet
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.model.build import Build
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory


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
    return (build.processor.id, build.is_virtualized)

def nth_builder(test, build, n):
    builder = None
    builders = test.builders.get(builder_key(build), [])
    try:
        builder = builders[n-1]
    except IndexError:
        pass
    return builder

def assign_to_builder(test, job_name, builder_number, processor='386'):
    build, bq = find_job(test, job_name, processor)
    builder = nth_builder(test, build, builder_number)
    bq.markAsBuilding(builder)


class TestBuildJobBase(TestCaseWithFactory):
    """Setup the test publisher and some builders."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestBuildJobBase, self).setUp()
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        self.i8 = self.factory.makeBuilder(name='i386-n-8', virtualized=False)
        self.i9 = self.factory.makeBuilder(name='i386-n-9', virtualized=False)

        processor_fam = ProcessorFamilySet().getByName('hppa')
        proc = processor_fam.processors[0]
        self.h6 = self.factory.makeBuilder(
            name='hppa-n-6', processor=proc, virtualized=False)
        self.h7 = self.factory.makeBuilder(
            name='hppa-n-7', processor=proc, virtualized=False)

        self.builders = dict()
        # x86 native
        self.builders[(1, False)] = [self.i8, self.i9]

        # hppa native
        self.builders[(3, True)] = [self.h6, self.h7]

        # Ensure all builders are operational.
        for builders in self.builders.values():
            for builder in builders:
                builder.builderok = True
                builder.manual = False

        # Disable the sample data builders.
        getUtility(IBuilderSet)['bob'].builderok = False
        getUtility(IBuilderSet)['frog'].builderok = False


class TestBuildPackageJob(TestBuildJobBase):
    """Test dispatch time estimates for binary builds (i.e. single build
    farm job type) targetting a single processor architecture and the primary
    archive.
    """
    def setUp(self):
        """Set up some native x86 builds for the test archive."""
        super(TestBuildPackageJob, self).setUp()
        # The builds will be set up as follows:
        #
        # j: 3        gedit p: hppa v:False e:0:01:00 *** s: 1001
        # j: 4        gedit p:  386 v:False e:0:02:00 *** s: 1002
        # j: 5      firefox p: hppa v:False e:0:03:00 *** s: 1003
        # j: 6      firefox p:  386 v:False e:0:04:00 *** s: 1004
        # j: 7     cobblers p: hppa v:False e:0:05:00 *** s: 1005
        # j: 8     cobblers p:  386 v:False e:0:06:00 *** s: 1006
        # j: 9 thunderpants p: hppa v:False e:0:07:00 *** s: 1007
        # j:10 thunderpants p:  386 v:False e:0:08:00 *** s: 1008
        # j:11          apg p: hppa v:False e:0:09:00 *** s: 1009
        # j:12          apg p:  386 v:False e:0:10:00 *** s: 1010
        # j:13          vim p: hppa v:False e:0:11:00 *** s: 1011
        # j:14          vim p:  386 v:False e:0:12:00 *** s: 1012
        # j:15          gcc p: hppa v:False e:0:13:00 *** s: 1013
        # j:16          gcc p:  386 v:False e:0:14:00 *** s: 1014
        # j:17        bison p: hppa v:False e:0:15:00 *** s: 1015
        # j:18        bison p:  386 v:False e:0:16:00 *** s: 1016
        # j:19         flex p: hppa v:False e:0:17:00 *** s: 1017
        # j:20         flex p:  386 v:False e:0:18:00 *** s: 1018
        # j:21     postgres p: hppa v:False e:0:19:00 *** s: 1019
        # j:22     postgres p:  386 v:False e:0:20:00 *** s: 1020
        #
        # j=job, p=processor, v=virtualized, e=estimated_duration, s=score

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
                sourcename="firefox",
                status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa,
                architecturehintlist='any').createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="cobblers",
                status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa,
                architecturehintlist='any').createMissingBuilds())
        self.builds.extend(
            self.publisher.getPubSource(
                sourcename="thunderpants",
                status=PackagePublishingStatus.PUBLISHED,
                archive=self.non_ppa,
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

    def test_x86_pending_queries(self):
        # Make sure the query returned by getPendingJobsQuery() selects the
        # proper jobs.
        #
        # The x86 builds are as follows:
        #
        # j: 4        gedit p:  386 v:False e:0:02:00 *** s: 1002
        # j: 6      firefox p:  386 v:False e:0:04:00 *** s: 1004
        # j: 8     cobblers p:  386 v:False e:0:06:00 *** s: 1006
        # j:10 thunderpants p:  386 v:False e:0:08:00 *** s: 1008
        # j:12          apg p:  386 v:False e:0:10:00 *** s: 1010
        # j:14          vim p:  386 v:False e:0:12:00 *** s: 1012
        # j:16          gcc p:  386 v:False e:0:14:00 *** s: 1014
        # j:18        bison p:  386 v:False e:0:16:00 *** s: 1016
        # j:20         flex p:  386 v:False e:0:18:00 *** s: 1018
        # j:22     postgres p:  386 v:False e:0:20:00 *** s: 1020
        #
        # Please note: the higher scored jobs are lower in the list.
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)

        build, bq = find_job(self, 'apg')
        bpj = bq.specific_job
        query = bpj.getPendingJobsQuery(1010, *builder_key(build))
        result_set = store.execute(query).get_all()
        # The pending x86 jobs with score 1010 or higher are as follows.
        # Please note that we do not require the results to be in any
        # particular order.

        # Processor == 1 -> Intel 386
        # SELECT id,name,title FROM processor
        #  id | name  |     title      
        # ----+-------+----------------
        #   1 | 386   | Intel 386
        #   2 | amd64 | AMD 64bit
        #   3 | hppa  | HPPA Processor

        expected_results = [
        #   job  score estimated_duration   processor   virtualized
            (12, 1010, timedelta(0, 600),       1,      False),
            (14, 1012, timedelta(0, 720),       1,      False),
            (16, 1014, timedelta(0, 840),       1,      False),
            (18, 1016, timedelta(0, 960),       1,      False),
            (20, 1018, timedelta(0, 1080),      1,      False),
            (22, 1020, timedelta(0, 1200),      1,      False)]
        self.assertEqual(sorted(result_set), sorted(expected_results))
        # How about builds with lower scores? Please note also that no
        # hppa builds are listed.
        query = bpj.getPendingJobsQuery(0, *builder_key(build))
        result_set = store.execute(query).get_all()
        expected_results = [
        #   job  score estimated_duration   processor   virtualized
            (22, 1020, timedelta(0, 1200),      1,      False),
            (20, 1018, timedelta(0, 1080),      1,      False),
            (18, 1016, timedelta(0, 960),       1,      False),
            (16, 1014, timedelta(0, 840),       1,      False),
            (14, 1012, timedelta(0, 720),       1,      False),
            (12, 1010, timedelta(0, 600),       1,      False),
            (10, 1008, timedelta(0, 480),       1,      False),
            (8,  1006, timedelta(0, 360),       1,      False),
            (6,  1004, timedelta(0, 240),       1,      False),
            (4,  1002, timedelta(0, 120),       1,      False)]
        self.assertEqual(sorted(result_set), sorted(expected_results))
        # How about builds with higher scores?
        query = bpj.getPendingJobsQuery(2500, *builder_key(build))
        result_set = store.execute(query).get_all()
        expected_results = []
        self.assertEqual(sorted(result_set), sorted(expected_results))

        # We will start the 'flex' job now and see whether it still turns
        # up in our pending job list.
        assign_to_builder(self, 'flex', 1)
        query = bpj.getPendingJobsQuery(1016, *builder_key(build))
        result_set = store.execute(query).get_all()
        expected_results = [
        #   job  score estimated_duration   processor   virtualized
            (22, 1020, timedelta(0, 1200),      1,      False),
            (18, 1016, timedelta(0, 960),       1,      False)]
        self.assertEqual(sorted(result_set), sorted(expected_results))
        # As we can see it was absent as expected.

    def test_hppa_pending_queries(self):
        # Make sure the query returned by getPendingJobsQuery() selects the
        # proper jobs.
        #
        # The hppa builds are as follows:
        #
        # j: 3        gedit p: hppa v:False e:0:01:00 *** s: 1001
        # j: 5      firefox p: hppa v:False e:0:03:00 *** s: 1003
        # j: 7     cobblers p: hppa v:False e:0:05:00 *** s: 1005
        # j: 9 thunderpants p: hppa v:False e:0:07:00 *** s: 1007
        # j:11          apg p: hppa v:False e:0:09:00 *** s: 1009
        # j:13          vim p: hppa v:False e:0:11:00 *** s: 1011
        # j:15          gcc p: hppa v:False e:0:13:00 *** s: 1013
        # j:17        bison p: hppa v:False e:0:15:00 *** s: 1015
        # j:19         flex p: hppa v:False e:0:17:00 *** s: 1017
        # j:21     postgres p: hppa v:False e:0:19:00 *** s: 1019
        #
        # Please note: the higher scored jobs are lower in the list.
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)

        build, bq = find_job(self, 'vim', 'hppa')
        bpj = bq.specific_job
        query = bpj.getPendingJobsQuery(1011, *builder_key(build))
        result_set = store.execute(query).get_all()
        # The pending hppa jobs with score 1011 or higher are as follows.
        # Please note that we do not require the results to be in any
        # particular order.

        # Processor == 3 -> HPPA
        # SELECT id,name,title FROM processor
        #  id | name  |     title      
        # ----+-------+----------------
        #   1 | 386   | Intel 386
        #   2 | amd64 | AMD 64bit
        #   3 | hppa  | HPPA Processor

        expected_results = [
        #   job  score estimated_duration   processor   virtualized
            (13, 1011, timedelta(0, 660),       3,      False),
            (15, 1013, timedelta(0, 780),       3,      False),
            (17, 1015, timedelta(0, 900),       3,      False),
            (19, 1017, timedelta(0, 1020),      3,      False),
            (21, 1019, timedelta(0, 1140),      3,      False)]
        self.assertEqual(sorted(result_set), sorted(expected_results))
        # How about builds with lower scores? Please note also that no
        # hppa builds are listed.
        query = bpj.getPendingJobsQuery(0, *builder_key(build))
        result_set = store.execute(query).get_all()
        expected_results = [
        #   job  score estimated_duration   processor   virtualized
            (3,  1001, timedelta(0, 60),        3,      False),
            (5,  1003, timedelta(0, 180),       3,      False),
            (7,  1005, timedelta(0, 300),       3,      False),
            (9,  1007, timedelta(0, 420),       3,      False),
            (11, 1009, timedelta(0, 540),       3,      False),
            (13, 1011, timedelta(0, 660),       3,      False),
            (15, 1013, timedelta(0, 780),       3,      False),
            (17, 1015, timedelta(0, 900),       3,      False),
            (19, 1017, timedelta(0, 1020),      3,      False),
            (21, 1019, timedelta(0, 1140),      3,      False)]
        self.assertEqual(sorted(result_set), sorted(expected_results))
        # How about builds with higher scores?
        query = bpj.getPendingJobsQuery(2500, *builder_key(build))
        result_set = store.execute(query).get_all()
        expected_results = []
        self.assertEqual(sorted(result_set), sorted(expected_results))

        # We will start the 'flex' job now and see whether it still turns
        # up in our pending job list.
        assign_to_builder(self, 'flex', 1, 'hppa')
        query = bpj.getPendingJobsQuery(1014, *builder_key(build))
        result_set = store.execute(query).get_all()
        expected_results = [
        #   job  score estimated_duration   processor   virtualized
            (17, 1015, timedelta(0, 900),       3,      False),
            (21, 1019, timedelta(0, 1140),      3,      False)]
        self.assertEqual(sorted(result_set), sorted(expected_results))
        # As we can see it was absent as expected.

    def test_processor(self):
        # Test that BuildPackageJob returns the correct processor.
        build, bq = find_job(self, 'gcc', '386')
        bpj = bq.specific_job
        self.assertEqual(bpj.processor.id, 1)
        build, bq = find_job(self, 'bison', 'hppa')
        bpj = bq.specific_job
        self.assertEqual(bpj.processor.id, 3)

    def test_virtualized(self):
        # Test that BuildPackageJob returns the correct virtualized flag.
        build, bq = find_job(self, 'apg', '386')
        bpj = bq.specific_job
        self.assertEqual(bpj.virtualized, False)
        build, bq = find_job(self, 'flex', 'hppa')
        bpj = bq.specific_job
        self.assertEqual(bpj.virtualized, False)
