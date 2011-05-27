# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test `DistroSeriesDifferenceJob` and utility."""

__metaclass__ = type

import transaction
from psycopg2 import ProgrammingError
from zope.component import getUtility
from zope.interface.verify import verifyObject

from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.launchpad.scripts.tests import run_script
from canonical.testing.layers import (
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )
from lp.registry.enum import (
    DistroSeriesDifferenceStatus,
    DistroSeriesDifferenceType,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.model.distroseriesdifference import DistroSeriesDifference
from lp.services.features.testing import FeatureFixture
from lp.services.job.interfaces.job import JobStatus
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.interfaces.distributionjob import (
    IDistroSeriesDifferenceJobSource,
    )
from lp.soyuz.model.distroseriesdifferencejob import (
    create_job,
    DistroSeriesDifferenceJob,
    FEATURE_FLAG_ENABLE_MODULE,
    find_waiting_jobs,
    make_metadata,
    may_require_job,
    )
from lp.testing import TestCaseWithFactory


def find_dsd_for(dsp, package):
    """Find `DistroSeriesDifference`.

    :param dsp: `DistroSeriesParent`.
    :param package: `SourcePackageName`.
    """
    store = IMasterStore(DistroSeriesDifference)
    return store.find(
        DistroSeriesDifference,
        DistroSeriesDifference.derived_series == dsp.derived_series,
        DistroSeriesDifference.parent_series == dsp.parent_series,
        DistroSeriesDifference.source_package_name == package)


class TestDistroSeriesDifferenceJobSource(TestCaseWithFactory):
    """Tests for `IDistroSeriesDifferenceJobSource`."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestDistroSeriesDifferenceJobSource, self).setUp()
        self.useFixture(FeatureFixture({FEATURE_FLAG_ENABLE_MODULE: u'on'}))

    def getJobSource(self):
        return getUtility(IDistroSeriesDifferenceJobSource)

    def makeDerivedDistroSeries(self):
        dsp = self.factory.makeDistroSeriesParent()
        return dsp.derived_series

    def test_baseline(self):
        verifyObject(IDistroSeriesDifferenceJobSource, self.getJobSource())

    def test_make_metadata_is_consistent(self):
        package = self.factory.makeSourcePackageName()
        parent_series = self.factory.makeDistroSeries()
        self.assertEqual(
            make_metadata(package, parent_series),
            make_metadata(package, parent_series))

    def test_make_metadata_distinguishes_packages(self):
        parent_series = self.factory.makeDistroSeries()
        one_package = self.factory.makeSourcePackageName()
        another_package = self.factory.makeSourcePackageName()
        self.assertNotEqual(
            make_metadata(one_package, parent_series),
            make_metadata(another_package, parent_series))

    def test_make_metadata_distinguishes_parents(self):
        package = self.factory.makeSourcePackageName()
        one_parent = self.factory.makeDistroSeries()
        another_parent = self.factory.makeDistroSeries()
        self.assertNotEqual(
            make_metadata(package, one_parent),
            make_metadata(package, another_parent))

    def test_may_require_job_accepts_none_derived_series(self):
        parent_series = self.factory.makeDistroSeriesParent().parent_series
        package = self.factory.makeSourcePackageName()
        self.assertFalse(may_require_job(None, package, parent_series))

    def test_may_require_job_accepts_none_parent_series(self):
        derived_series = self.makeDerivedDistroSeries()
        package = self.factory.makeSourcePackageName()
        self.assertTrue(may_require_job(derived_series, package, None))

    def test_may_require_job_allows_new_jobs(self):
        dsp = self.factory.makeDistroSeriesParent()
        package = self.factory.makeSourcePackageName()
        self.assertTrue(may_require_job(
            dsp.derived_series, package, dsp.parent_series))

    def test_may_require_job_forbids_redundant_jobs(self):
        dsp = self.factory.makeDistroSeriesParent()
        package = self.factory.makeSourcePackageName()
        create_job(dsp.derived_series, package, dsp.parent_series)
        self.assertFalse(
            may_require_job(dsp.derived_series, package, dsp.parent_series))

    def test_may_require_job_forbids_jobs_on_nonderived_series(self):
        sourcepackage = self.factory.makeSourcePackage()
        self.assertFalse(may_require_job(
            sourcepackage.distroseries, sourcepackage.sourcepackagename,
            None))

    def test_may_require_job_forbids_jobs_for_intra_distro_derivation(self):
        package = self.factory.makeSourcePackageName()
        parent = self.factory.makeDistroSeries()
        child = self.factory.makeDistroSeries(
            distribution=parent.distribution, previous_series=parent)
        self.assertFalse(may_require_job(child, package, parent))

    def test_may_require_job_only_considers_waiting_jobs_for_redundancy(self):
        dsp = self.factory.makeDistroSeriesParent()
        package = self.factory.makeSourcePackageName()
        existing_job = create_job(
            dsp.derived_series, package, dsp.parent_series)
        existing_job.job.start()
        self.assertTrue(
            may_require_job(dsp.derived_series, package, dsp.parent_series))

    def test_create_job_creates_waiting_job(self):
        dsp = self.factory.makeDistroSeriesParent()
        package = self.factory.makeSourcePackageName()
        dsdjob = create_job(dsp.derived_series, package, dsp.parent_series)
        self.assertEqual(JobStatus.WAITING, dsdjob.job.status)

    def find_waiting_jobs_finds_waiting_jobs(self):
        dsp = self.factory.makeDistroSeriesParent()
        package = self.factory.makeSourcePackageName()
        job = create_job(dsp.derived_series, package, dsp.parent_series)
        self.assertContentEqual(
            [job],
            find_waiting_jobs(dsp.derived_series, package, dsp.parent_series))

    def find_waiting_jobs_ignores_other_derived_series(self):
        dsp = self.factory.makeDistroSeriesParent()
        package = self.factory.makeSourcePackageName()
        create_job(dsp.derived_series, package, dsp.parent_series)
        other_series = self.factory.makeDistroSeries()
        self.assertContentEqual(
            [], find_waiting_jobs(other_series, package, dsp.parent_series))

    def find_waiting_jobs_ignores_other_parent_series(self):
        dsp = self.factory.makeDistroSeriesParent()
        package = self.factory.makeSourcePackageName()
        create_job(dsp.derived_series, package, dsp.parent_series)
        other_series = self.factory.makeDistroSeries()
        self.assertContentEqual(
            [], find_waiting_jobs(dsp.derived_series, package, other_series))

    def find_waiting_jobs_ignores_other_packages(self):
        dsp = self.factory.makeDistroSeriesParent()
        package = self.factory.makeSourcePackageName()
        create_job(dsp.derived_series, package, dsp.parent_series)
        other_package = self.factory.makeSourcePackageName()
        self.assertContentEqual(
            [],
            find_waiting_jobs(
                dsp.derived_series, other_package, dsp.parent_series))

    def find_waiting_jobs_considers_only_waiting_jobs(self):
        dsp = self.factory.makeDistroSeriesParent()
        package = self.factory.makeSourcePackageName()
        job = create_job(dsp.derived_series, package, dsp.parent_series)
        job.start()
        self.assertContentEqual(
            [],
            find_waiting_jobs(dsp.derived_series, package, dsp.parent_series))
        job.complete()
        self.assertContentEqual(
            [],
            find_waiting_jobs(dsp.derived_series, package, dsp.parent_series))

    def test_createForPackagedPublication_creates_jobs_for_its_child(self):
        dsp = self.factory.makeDistroSeriesParent()
        parent_dsp = self.factory.makeDistroSeriesParent(
            derived_series=dsp.parent_series)
        package = self.factory.makeSourcePackageName()
        # Create a job for the derived_series parent, which should create
        # two jobs. One for derived_series, and the other for its child.
        self.getJobSource().createForPackagePublication(
            parent_dsp.derived_series, package,
            PackagePublishingPocket.RELEASE, parent_dsp.parent_series)
        jobs = sum([
            find_waiting_jobs(dsp.derived_series, package, dsp.parent_series)
            for dsp in [parent_dsp, parent_dsp]],
            [])
        self.assertEqual(
            [package.id, package.id],
            [job.metadata["sourcepackagename"] for job in jobs])

    def test_createForPackagePublication_creates_job_for_derived_series(self):
        dsp = self.factory.makeDistroSeriesParent()
        package = self.factory.makeSourcePackageName()
        self.getJobSource().createForPackagePublication(
            dsp.derived_series, package, PackagePublishingPocket.RELEASE,
            dsp.parent_series)
        jobs = find_waiting_jobs(
            dsp.derived_series, package, dsp.parent_series)
        self.assertEqual(
            [package.id], [job.metadata["sourcepackagename"] for job in jobs])

    def test_createForPackagePublication_obeys_feature_flag(self):
        dsp = self.factory.makeDistroSeriesParent()
        package = self.factory.makeSourcePackageName()
        self.useFixture(FeatureFixture({FEATURE_FLAG_ENABLE_MODULE: ''}))
        self.getJobSource().createForPackagePublication(
            dsp.derived_series, package, PackagePublishingPocket.RELEASE,
            dsp.parent_series)
        self.assertContentEqual(
            [],
            find_waiting_jobs(dsp.derived_series, package, dsp.parent_series))

    def test_createForPackagePublication_ignores_backports_and_proposed(self):
        dsp = self.factory.makeDistroSeriesParent()
        package = self.factory.makeSourcePackageName()
        self.getJobSource().createForPackagePublication(
            dsp.derived_series, package, PackagePublishingPocket.BACKPORTS,
            dsp.parent_series)
        self.getJobSource().createForPackagePublication(
            dsp.derived_series, package, PackagePublishingPocket.PROPOSED,
            dsp.parent_series)
        self.assertContentEqual(
            [],
            find_waiting_jobs(dsp.derived_series, package, dsp.parent_series))

    def test_cronscript(self):
        dsp = self.factory.makeDistroSeriesParent()
        package = self.factory.makeSourcePackageName()
        self.getJobSource().createForPackagePublication(
            dsp.derived_series, package, PackagePublishingPocket.RELEASE,
            dsp.parent_series)
        # Make changes visible to the process we'll be spawning.
        transaction.commit()
        return_code, stdout, stderr = run_script(
            'cronscripts/distroseriesdifference_job.py', ['-v'])
        # The cronscript ran how we expected it to.
        self.assertEqual(return_code, 0)
        self.assertIn(
            'INFO    Ran 1 DistroSeriesDifferenceJob jobs.', stderr)
        # And it did what we expected.
        jobs = find_waiting_jobs(
            dsp.derived_series, package, dsp.parent_series)
        self.assertContentEqual([], jobs)
        self.assertEqual(1, find_dsd_for(dsp, package).count())

    def test_job_runner_does_not_create_multiple_dsds(self):
        dsp = self.factory.makeDistroSeriesParent()
        package = self.factory.makeSourcePackageName()
        job = self.getJobSource().createForPackagePublication(
            dsp.derived_series, package, PackagePublishingPocket.RELEASE,
            dsp.parent_series)
        job[0].start()
        job[0].run()
        # Complete the job so we can create another.
        job[0].job.complete()
        # The first job would have created a DSD for us.
        self.assertEqual(1, find_dsd_for(dsp, package).count())
        # If we run the job again, it will not create another DSD.
        job = self.getJobSource().createForPackagePublication(
            dsp.derived_series, package, PackagePublishingPocket.RELEASE,
            dsp.parent_series)
        job[0].start()
        job[0].run()
        self.assertEqual(1, find_dsd_for(dsp, package).count())

    def test_packageset_filter_passes_inherited_packages(self):
        dsp = self.factory.makeDistroSeriesParent()
        # Parent must have a packageset or the filter will pass anyway.
        self.factory.makePackageset(distroseries=dsp.parent_series)
        package = self.factory.makeSourcePackageName()
        # Package is not in the packageset _but_ both the parent and
        # derived series have it.
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=dsp.parent_series, sourcepackagename=package)
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=dsp.derived_series, sourcepackagename=package)
        job = create_job(dsp.derived_series, package, dsp.parent_series)
        self.assertTrue(job.passesPackagesetFilter())

    def test_packageset_filter_passes_packages_unique_to_derived_series(self):
        dsp = self.factory.makeDistroSeriesParent()
        # Parent must have a packageset or the filter will pass anyway.
        self.factory.makePackageset(distroseries=dsp.parent_series)
        package = self.factory.makeSourcePackageName()
        # Package exists in the derived series but not in the parent
        # series.
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=dsp.derived_series, sourcepackagename=package)
        job = create_job(dsp.derived_series, package, dsp.parent_series)
        self.assertTrue(job.passesPackagesetFilter())

    def test_packageset_filter_passes_all_if_parent_has_no_packagesets(self):
        # Debian in particular has no packagesets.  If the parent series
        # has no packagesets, the packageset filter passes all packages.
        dsp = self.factory.makeDistroSeriesParent()
        package = self.factory.makeSourcePackageName()
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=dsp.parent_series, sourcepackagename=package)
        job = create_job(dsp.derived_series, package, dsp.parent_series)
        self.assertTrue(job.passesPackagesetFilter())

    def makeInheritedPackageSet(self, distro_series_parent, packages=()):
        """Simulate an inherited `Packageset`.

        Creates a packageset in the parent that has an equivalent in
        `derived_series`.
        """
        parent_packageset = self.factory.makePackageset(
            distroseries=distro_series_parent.parent_series,
            packages=packages)
        return self.factory.makePackageset(
            distroseries=distro_series_parent.derived_series,
            packages=packages, name=parent_packageset.name,
            owner=parent_packageset.owner, related_set=parent_packageset)

    def test_packageset_filter_passes_package_in_inherited_packageset(self):
        dsp = self.factory.makeDistroSeriesParent()
        # Package is in a packageset on the parent that the derived
        # series also has.
        package = self.factory.makeSourcePackageName()
        self.makeInheritedPackageSet(dsp, [package])
        # Package is in parent series and in a packageset that the
        # derived series inherited.
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=dsp.parent_series, sourcepackagename=package)
        job = create_job(dsp.derived_series, package, dsp.parent_series)
        self.assertTrue(job.passesPackagesetFilter())

    def test_packageset_filter_blocks_unwanted_parent_package(self):
        dsp = self.factory.makeDistroSeriesParent()
        self.makeInheritedPackageSet(dsp)
        package = self.factory.makeSourcePackageName()
        # Package is in the parent series but not in a packageset shared
        # between the derived series and the parent series.
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=dsp.parent_series, sourcepackagename=package)
        job = create_job(dsp.derived_series, package, dsp.parent_series)
        self.assertFalse(job.passesPackagesetFilter())


class TestDistroSeriesDifferenceJobEndToEnd(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestDistroSeriesDifferenceJobEndToEnd, self).setUp()
        self.useFixture(FeatureFixture({FEATURE_FLAG_ENABLE_MODULE: u'on'}))
        self.store = IMasterStore(DistroSeriesDifference)

    def getJobSource(self):
        return getUtility(IDistroSeriesDifferenceJobSource)

    def makeDerivedDistroSeries(self):
        dsp = self.factory.makeDistroSeriesParent()
        return dsp

    def createPublication(self, source_package_name, versions, distroseries,
                          archive=None):
        if archive is None:
            archive = distroseries.main_archive
        changelog_lfa = self.factory.makeChangelog(
            source_package_name.name, versions)
        # Commit for the Librarian's sake.
        transaction.commit()
        spr = self.factory.makeSourcePackageRelease(
            sourcepackagename=source_package_name, version=versions[0],
            changelog=changelog_lfa)
        return self.factory.makeSourcePackagePublishingHistory(
            sourcepackagerelease=spr, archive=archive,
            distroseries=distroseries,
            status=PackagePublishingStatus.PUBLISHED,
            pocket=PackagePublishingPocket.RELEASE)

    def findDSD(self, derived_series, source_package_name):
        return self.store.find(
            DistroSeriesDifference,
            DistroSeriesDifference.derived_series == derived_series,
            DistroSeriesDifference.source_package_name ==
            source_package_name)

    def runJob(self, job):
        transaction.commit()
        self.layer.switchDbUser('distroseriesdifferencejob')
        dsdjob = DistroSeriesDifferenceJob(job)
        dsdjob.start()
        dsdjob.run()
        dsdjob.complete()
        transaction.commit()
        self.layer.switchDbUser('launchpad')

    def test_parent_gets_newer(self):
        # When a new source package is uploaded to the parent distroseries,
        # a job is created that updates the relevant DSD.
        dsp = self.makeDerivedDistroSeries()
        source_package_name = self.factory.makeSourcePackageName()
        self.createPublication(
            source_package_name, ['1.0-1derived1', '1.0-1'],
            dsp.derived_series)
        self.createPublication(
            source_package_name, ['1.0-1'], dsp.parent_series)

        # Creating the SPPHs has created jobs for us, so grab them off
        # the queue.
        jobs = find_waiting_jobs(dsp.derived_series, source_package_name)
        self.runJob(jobs[0])
        ds_diff = find_dsd_for(dsp, source_package_name)
        self.assertEqual(1, ds_diff.count())
        self.assertEqual('1.0-1', ds_diff[0].parent_source_version)
        self.assertEqual('1.0-1derived1', ds_diff[0].source_version)
        self.assertEqual('1.0-1', ds_diff[0].base_version)
        # Now create a 1.0-2 upload to the parent.
        self.createPublication(
            source_package_name, ['1.0-2', '1.0-1'],
            dsp.parent_series)
        jobs = find_waiting_jobs(dsp.derived_series, source_package_name)
        self.runJob(jobs[0])
        # And the DSD we have a hold of will have updated.
        self.assertEqual('1.0-2', ds_diff[0].parent_source_version)
        self.assertEqual('1.0-1derived1', ds_diff[0].source_version)
        self.assertEqual('1.0-1', ds_diff[0].base_version)

    def test_child_gets_newer(self):
        # When a new source is uploaded to the child distroseries, the DSD is
        # updated and auto-blacklisted.
        dsp = self.makeDerivedDistroSeries()
        source_package_name = self.factory.makeSourcePackageName()
        self.createPublication(
            source_package_name, ['1.0-1'], dsp.derived_series)
        self.createPublication(
            source_package_name, ['1.0-1'], dsp.parent_series)
        jobs = find_waiting_jobs(dsp.derived_series, source_package_name)
        self.runJob(jobs[0])
        ds_diff = find_dsd_for(dsp, source_package_name)
        self.assertEqual(
            DistroSeriesDifferenceStatus.RESOLVED, ds_diff[0].status)
        self.createPublication(
            source_package_name, ['2.0-0derived1', '1.0-1'],
            dsp.derived_series)
        jobs = find_waiting_jobs(dsp.derived_series, source_package_name)
        self.runJob(jobs[0])
        self.assertEqual(
            DistroSeriesDifferenceStatus.BLACKLISTED_CURRENT,
            ds_diff[0].status)
        self.assertEqual('1.0-1', ds_diff[0].base_version)

    def test_child_is_synced(self):
        # If the source package gets 'synced' to the child from the parent,
        # the job correctly updates the DSD.
        dsp = self.makeDerivedDistroSeries()
        derived_series = dsp.derived_series
        source_package_name = self.factory.makeSourcePackageName()
        self.createPublication(
            source_package_name, ['1.0-1derived1', '1.0-1'], derived_series)
        self.createPublication(
            source_package_name, ['1.0-2', '1.0-1'], dsp.parent_series)
        jobs = find_waiting_jobs(derived_series, source_package_name)
        self.runJob(jobs[0])
        ds_diff = self.findDSD(derived_series, source_package_name)
        self.assertEqual('1.0-1', ds_diff[0].base_version)
        self.createPublication(
            source_package_name, ['1.0-2', '1.0-1'], derived_series)
        jobs = find_waiting_jobs(derived_series, source_package_name)
        self.runJob(jobs[0])
        self.assertEqual(
            DistroSeriesDifferenceStatus.RESOLVED, ds_diff[0].status)

    def test_only_in_child(self):
        # If a source package only exists in the child distroseries, the DSD
        # is created with the right type.
        dsp = self.makeDerivedDistroSeries()
        derived_series = dsp.derived_series
        source_package_name = self.factory.makeSourcePackageName()
        self.createPublication(
            source_package_name, ['1.0-0derived1'], derived_series)
        jobs = find_waiting_jobs(derived_series, source_package_name)
        self.runJob(jobs[0])
        ds_diff = self.findDSD(derived_series, source_package_name)
        self.assertEqual(
            DistroSeriesDifferenceType.UNIQUE_TO_DERIVED_SERIES,
            ds_diff[0].difference_type)

    def test_only_in_parent(self):
        # If a source package only exists in the parent distroseries, the DSD
        # is created with the right type.
        dsp = self.makeDerivedDistroSeries()
        derived_series = dsp.derived_series
        source_package_name = self.factory.makeSourcePackageName()
        self.createPublication(
            source_package_name, ['1.0-1'], dsp.parent_series)
        jobs = find_waiting_jobs(derived_series, source_package_name)
        self.runJob(jobs[0])
        ds_diff = self.findDSD(derived_series, source_package_name)
        self.assertEqual(
            DistroSeriesDifferenceType.MISSING_FROM_DERIVED_SERIES,
            ds_diff[0].difference_type)

    def test_deleted_in_parent(self):
        # If a source package is deleted in the parent, a job is created, and
        # the DSD is updated correctly.
        dsp = self.makeDerivedDistroSeries()
        derived_series = dsp.derived_series
        source_package_name = self.factory.makeSourcePackageName()
        self.createPublication(
            source_package_name, ['1.0-1'], derived_series)
        spph = self.createPublication(
            source_package_name, ['1.0-1'], dsp.parent_series)
        jobs = find_waiting_jobs(derived_series, source_package_name)
        self.runJob(jobs[0])
        ds_diff = self.findDSD(derived_series, source_package_name)
        self.assertEqual(
            DistroSeriesDifferenceStatus.RESOLVED, ds_diff[0].status)
        spph.requestDeletion(self.factory.makePerson())
        jobs = find_waiting_jobs(derived_series, source_package_name)
        self.runJob(jobs[0])
        self.assertEqual(
            DistroSeriesDifferenceType.UNIQUE_TO_DERIVED_SERIES,
            ds_diff[0].difference_type)

    def test_deleted_in_child(self):
        # If a source package is deleted in the child, a job is created, and
        # the DSD is updated correctly.
        dsp = self.makeDerivedDistroSeries()
        derived_series = dsp.derived_series
        source_package_name = self.factory.makeSourcePackageName()
        spph = self.createPublication(
            source_package_name, ['1.0-1'], derived_series)
        self.createPublication(
            source_package_name, ['1.0-1'], dsp.parent_series)
        jobs = find_waiting_jobs(derived_series, source_package_name)
        self.runJob(jobs[0])
        ds_diff = self.findDSD(derived_series, source_package_name)
        self.assertEqual(
            DistroSeriesDifferenceStatus.RESOLVED, ds_diff[0].status)
        spph.requestDeletion(self.factory.makePerson())
        jobs = find_waiting_jobs(derived_series, source_package_name)
        self.runJob(jobs[0])
        self.assertEqual(
            DistroSeriesDifferenceType.MISSING_FROM_DERIVED_SERIES,
            ds_diff[0].difference_type)

    def test_no_job_for_PPA(self):
        # If a source package is uploaded to a PPA, a job is not created.
        dsp = self.makeDerivedDistroSeries()
        source_package_name = self.factory.makeSourcePackageName()
        ppa = self.factory.makeArchive()
        self.createPublication(
            source_package_name, ['1.0-1'], dsp.derived_series, ppa)
        self.assertContentEqual(
            [], find_waiting_jobs(dsp.derived_series, source_package_name))

    def test_no_job_for_PPA_with_deleted_source(self):
        # If a source package is deleted from a PPA, no job is created.
        dsp = self.makeDerivedDistroSeries()
        derived_series = dsp.derived_series
        source_package_name = self.factory.makeSourcePackageName()
        ppa = self.factory.makeArchive()
        spph = self.createPublication(
            source_package_name, ['1.0-1'], derived_series, ppa)
        spph.requestDeletion(ppa.owner)
        self.assertContentEqual(
            [], find_waiting_jobs(derived_series, source_package_name))

    def test_update_deletes_diffs(self):
        # When a DSD is updated, the diffs are invalidated.
        dsp = self.makeDerivedDistroSeries()
        derived_series = dsp.derived_series
        source_package_name = self.factory.makeSourcePackageName()
        self.createPublication(
            source_package_name, ['1.0-1derived1', '1.0-1'], derived_series)
        self.createPublication(
            source_package_name, ['1.0-2', '1.0-1'], dsp.parent_series)
        spr = self.factory.makeSourcePackageRelease(
            sourcepackagename=source_package_name, version='1.0-1')
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagerelease=spr,
            archive=dsp.parent_series.main_archive,
            distroseries=dsp.parent_series,
            status=PackagePublishingStatus.SUPERSEDED)
        jobs = find_waiting_jobs(derived_series, source_package_name)
        self.runJob(jobs[0])
        ds_diff = self.findDSD(derived_series, source_package_name)
        ds_diff[0].requestPackageDiffs(self.factory.makePerson())
        self.assertIsNot(None, ds_diff[0].package_diff)
        self.assertIsNot(None, ds_diff[0].parent_package_diff)
        self.createPublication(
            source_package_name, ['1.0-3', '1.0-2', '1.0-1'],
            dsp.parent_series)
        jobs = find_waiting_jobs(derived_series, source_package_name)
        self.runJob(jobs[0])
        # Since the diff showing the changes from 1.0-1 to 1.0-1derived1 is
        # still valid, it isn't reset, but the parent diff is.
        self.assertIsNot(None, ds_diff[0].package_diff)
        self.assertIs(None, ds_diff[0].parent_package_diff)


class TestDistroSeriesDifferenceJobPermissions(TestCaseWithFactory):
    """Database permissions test for `DistroSeriesDifferenceJob`."""

    layer = LaunchpadZopelessLayer

    def test_permissions(self):
        script_users = [
            'archivepublisher',
            'gina',
            'queued',
            'uploader',
            ]
        dsp = self.factory.makeDistroSeriesParent()
        parent = dsp.parent_series
        derived = dsp.derived_series
        packages = dict(
            (user, self.factory.makeSourcePackageName())
            for user in script_users)
        transaction.commit()
        for user in script_users:
            self.layer.switchDbUser(user)
            try:
                create_job(derived, packages[user], parent)
            except ProgrammingError, e:
                self.assertTrue(
                    False,
                    "Database role %s was unable to create a job.  "
                    "Error was: %s" % (user, e))

        # The test is that we get here without exceptions.
        pass
