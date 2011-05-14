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


class TestDistroSeriesDifferenceJobSource(TestCaseWithFactory):
    """Tests for `IDistroSeriesDifferenceJobSource`."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestDistroSeriesDifferenceJobSource, self).setUp()
        self.useFixture(FeatureFixture({FEATURE_FLAG_ENABLE_MODULE: u'on'}))

    def getJobSource(self):
        return getUtility(IDistroSeriesDifferenceJobSource)

    def makeDerivedDistroSeries(self):
        return self.factory.makeDistroSeries(
            parent_series=self.factory.makeDistroSeries())

    def test_baseline(self):
        verifyObject(IDistroSeriesDifferenceJobSource, self.getJobSource())

    def test_make_metadata_is_consistent(self):
        package = self.factory.makeSourcePackageName()
        self.assertEqual(make_metadata(package), make_metadata(package))

    def test_make_metadata_distinguishes_packages(self):
        one_package = self.factory.makeSourcePackageName()
        another_package = self.factory.makeSourcePackageName()
        self.assertNotEqual(
            make_metadata(one_package), make_metadata(another_package))

    def test_may_require_job_accepts_none_distroseries(self):
        package = self.factory.makeSourcePackageName()
        self.assertFalse(may_require_job(None, package))

    def test_may_require_job_allows_new_jobs(self):
        distroseries = self.makeDerivedDistroSeries()
        package = self.factory.makeSourcePackageName()
        self.assertTrue(may_require_job(distroseries, package))

    def test_may_require_job_forbids_redundant_jobs(self):
        distroseries = self.makeDerivedDistroSeries()
        package = self.factory.makeSourcePackageName()
        create_job(distroseries, package)
        self.assertFalse(may_require_job(distroseries, package))

    def test_may_require_job_forbids_jobs_on_nonderived_series(self):
        sourcepackage = self.factory.makeSourcePackage()
        self.assertFalse(may_require_job(
            sourcepackage.distroseries, sourcepackage.sourcepackagename))

    def test_may_require_job_forbids_jobs_for_intra_distro_derivation(self):
        package = self.factory.makeSourcePackageName()
        parent = self.factory.makeDistroSeries()
        child = self.factory.makeDistroSeries(
            distribution=parent.distribution, previous_series=parent)
        self.assertFalse(may_require_job(child, package))

    def test_may_require_job_only_considers_waiting_jobs_for_redundancy(self):
        distroseries = self.makeDerivedDistroSeries()
        package = self.factory.makeSourcePackageName()
        existing_job = create_job(distroseries, package)
        existing_job.job.start()
        self.assertTrue(may_require_job(distroseries, package))

    def test_create_job_creates_waiting_job(self):
        distroseries = self.makeDerivedDistroSeries()
        package = self.factory.makeSourcePackageName()
        dsdjob = create_job(distroseries, package)
        self.assertEqual(JobStatus.WAITING, dsdjob.job.status)

    def find_waiting_jobs_finds_waiting_jobs(self):
        sourcepackage = self.factory.makeSourcePackage()
        distroseries, sourcepackagename = (
            sourcepackage.distroseries, sourcepackage.distroseries)
        job = create_job(distroseries, sourcepackagename)
        self.assertContentEqual(
            [job], find_waiting_jobs(distroseries, sourcepackagename))

    def find_waiting_jobs_ignores_other_series(self):
        sourcepackage = self.factory.makeSourcePackage()
        distroseries, sourcepackagename = (
            sourcepackage.distroseries, sourcepackage.distroseries)
        create_job(distroseries, sourcepackagename)
        other_series = self.factory.makeDistroSeries()
        self.assertContentEqual(
            [], find_waiting_jobs(other_series, sourcepackagename))

    def find_waiting_jobs_ignores_other_packages(self):
        sourcepackage = self.factory.makeSourcePackage()
        distroseries, sourcepackagename = (
            sourcepackage.distroseries, sourcepackage.distroseries)
        create_job(distroseries, sourcepackagename)
        other_spn = self.factory.makeSourcePackageName()
        self.assertContentEqual(
            [], find_waiting_jobs(distroseries, other_spn))

    def find_waiting_jobs_considers_only_waiting_jobs(self):
        sourcepackage = self.factory.makeSourcePackage()
        distroseries, sourcepackagename = (
            sourcepackage.distroseries, sourcepackage.distroseries)
        job = create_job(distroseries, sourcepackagename)
        job.start()
        self.assertContentEqual(
            [], find_waiting_jobs(distroseries, sourcepackagename))
        job.complete()
        self.assertContentEqual(
            [], find_waiting_jobs(distroseries, sourcepackagename))

    def test_createForPackagedPublication_creates_jobs_for_its_child(self):
        derived_series = self.factory.makeDistroSeries(
            parent_series=self.makeDerivedDistroSeries())
        package = self.factory.makeSourcePackageName()
        # Create a job for the derived_series parent, which should create
        # two jobs. One for derived_series, and the other for its child.
        self.getJobSource().createForPackagePublication(
            derived_series.parent_series, package,
            PackagePublishingPocket.RELEASE)
        jobs = (list(
            find_waiting_jobs(derived_series.parent_series, package)) +
            list(find_waiting_jobs(derived_series, package)))
        self.assertEqual(2, len(jobs))
        self.assertEqual(package.id, jobs[0].metadata['sourcepackagename'])
        self.assertEqual(package.id, jobs[1].metadata['sourcepackagename'])
        # Lastly, a job was not created for the grandparent.
        jobs = list(
            find_waiting_jobs(derived_series.parent_series.parent_series,
                package))
        self.assertEqual(0, len(jobs))

    def test_createForPackagePublication_creates_job_for_derived_series(self):
        derived_series = self.makeDerivedDistroSeries()
        package = self.factory.makeSourcePackageName()
        self.getJobSource().createForPackagePublication(
            derived_series, package, PackagePublishingPocket.RELEASE)
        jobs = list(find_waiting_jobs(derived_series, package))
        self.assertEqual(1, len(jobs))
        self.assertEqual(package.id, jobs[0].metadata['sourcepackagename'])

    def test_createForPackagePublication_obeys_feature_flag(self):
        distroseries = self.makeDerivedDistroSeries()
        package = self.factory.makeSourcePackageName()
        self.useFixture(FeatureFixture({FEATURE_FLAG_ENABLE_MODULE: ''}))
        self.getJobSource().createForPackagePublication(
            distroseries, package, PackagePublishingPocket.RELEASE)
        self.assertContentEqual([], find_waiting_jobs(distroseries, package))

    def test_createForPackagePublication_ignores_backports_and_proposed(self):
        distroseries = self.makeDerivedDistroSeries()
        package = self.factory.makeSourcePackageName()
        self.getJobSource().createForPackagePublication(
            distroseries, package, PackagePublishingPocket.BACKPORTS)
        self.getJobSource().createForPackagePublication(
            distroseries, package, PackagePublishingPocket.PROPOSED)
        self.assertContentEqual([], find_waiting_jobs(distroseries, package))

    def test_cronscript(self):
        derived_series = self.makeDerivedDistroSeries()
        package = self.factory.makeSourcePackageName()
        self.getJobSource().createForPackagePublication(
            derived_series, package, PackagePublishingPocket.RELEASE)
        transaction.commit() # The cronscript is a different process.
        return_code, stdout, stderr = run_script(
            'cronscripts/distroseriesdifference_job.py', ['-v'])
        # The cronscript ran how we expected it to.
        self.assertEqual(return_code, 0)
        self.assertIn(
            'INFO    Ran 1 DistroSeriesDifferenceJob jobs.', stderr)
        # And it did what we expected.
        jobs = list(find_waiting_jobs(derived_series, package))
        self.assertEqual(0, len(jobs))
        store = IMasterStore(DistroSeriesDifference)
        ds_diff = store.find(
            DistroSeriesDifference,
            DistroSeriesDifference.derived_series == derived_series,
            DistroSeriesDifference.source_package_name == package)
        self.assertEqual(1, ds_diff.count())

    def test_job_runner_does_not_create_multiple_dsds(self):
        derived_series = self.makeDerivedDistroSeries()
        package = self.factory.makeSourcePackageName()
        job = self.getJobSource().createForPackagePublication(
            derived_series, package, PackagePublishingPocket.RELEASE)
        job[0].start()
        job[0].run()
        job[0].job.complete() # So we can create another job.
        # The first job would have created a DSD for us.
        store = IMasterStore(DistroSeriesDifference)
        ds_diff = store.find(
            DistroSeriesDifference,
            DistroSeriesDifference.derived_series == derived_series,
            DistroSeriesDifference.source_package_name == package)
        self.assertEqual(1, ds_diff.count())
        # If we run the job again, it will not create another DSD.
        job = self.getJobSource().createForPackagePublication(
            derived_series, package, PackagePublishingPocket.RELEASE)
        job[0].start()
        job[0].run()
        ds_diff = store.find(
            DistroSeriesDifference,
            DistroSeriesDifference.derived_series == derived_series,
            DistroSeriesDifference.source_package_name == package)
        self.assertEqual(1, ds_diff.count())

    def test_packageset_filter_passes_inherited_packages(self):
        derived_series = self.makeDerivedDistroSeries()
        parent_series = derived_series.parent_series
        # Parent must have a packageset or the filter will pass anyway.
        self.factory.makePackageset(distroseries=parent_series)
        package = self.factory.makeSourcePackageName()
        # Package is not in the packageset _but_ both the parent and
        # derived series have it.
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=parent_series, sourcepackagename=package)
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=derived_series, sourcepackagename=package)
        job = create_job(derived_series, package)
        self.assertTrue(job.passesPackagesetFilter())

    def test_packageset_filter_passes_packages_unique_to_derived_series(self):
        derived_series = self.makeDerivedDistroSeries()
        parent_series = derived_series.parent_series
        # Parent must have a packageset or the filter will pass anyway.
        self.factory.makePackageset(distroseries=parent_series)
        package = self.factory.makeSourcePackageName()
        # Package exists in the derived series but not in the parent
        # series.
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=derived_series, sourcepackagename=package)
        job = create_job(derived_series, package)
        self.assertTrue(job.passesPackagesetFilter())

    def test_packageset_filter_passes_all_if_parent_has_no_packagesets(self):
        # Debian in particular has no packagesets.  If the parent series
        # has no packagesets, the packageset filter passes all packages.
        derived_series = self.makeDerivedDistroSeries()
        parent_series = derived_series.parent_series
        package = self.factory.makeSourcePackageName()
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=parent_series, sourcepackagename=package)
        job = create_job(derived_series, package)
        self.assertTrue(job.passesPackagesetFilter())

    def makeInheritedPackageSet(self, derived_series, packages=()):
        """Simulate an inherited `Packageset`.

        Creates a packageset in the parent that has an equivalent in
        `derived_series`.
        """
        parent_series = derived_series.parent_series
        parent_packageset = self.factory.makePackageset(
            distroseries=parent_series, packages=packages)
        derived_packageset = self.factory.makePackageset(
            distroseries=derived_series, packages=packages,
            name=parent_packageset.name, owner=parent_packageset.owner,
            related_set=parent_packageset)

    def test_packageset_filter_passes_package_in_inherited_packageset(self):
        derived_series = self.makeDerivedDistroSeries()
        parent_series = derived_series.parent_series
        # Package is in a packageset on the parent that the derived
        # series also has.
        package = self.factory.makeSourcePackageName()
        self.makeInheritedPackageSet(derived_series, [package])
        # Package is in parent series and in a packageset that the
        # derived series inherited.
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=parent_series, sourcepackagename=package)
        job = create_job(derived_series, package)
        self.assertTrue(job.passesPackagesetFilter())

    def test_packageset_filter_blocks_unwanted_parent_package(self):
        derived_series = self.makeDerivedDistroSeries()
        parent_series = derived_series.parent_series
        self.makeInheritedPackageSet(derived_series)
        package = self.factory.makeSourcePackageName()
        # Package is in the parent series but not in a packageset shared
        # between the derived series and the parent series.
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=parent_series, sourcepackagename=package)
        job = create_job(derived_series, package)
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
        return self.factory.makeDistroSeries(
            parent_series=self.factory.makeDistroSeries())

    def createPublication(self, source_package_name, versions, distroseries,
                          archive=None):
        if archive is None:
            archive = distroseries.main_archive
        changelog_lfa = self.factory.makeChangelog(
            source_package_name.name, versions)
        transaction.commit() # Yay, librarian.
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
        transaction.commit() # Switching DB user performs an abort.
        self.layer.switchDbUser('distroseriesdifferencejob')
        dsdjob = DistroSeriesDifferenceJob(job)
        dsdjob.start()
        dsdjob.run()
        dsdjob.complete()
        transaction.commit() # Switching DB user performs an abort.
        self.layer.switchDbUser('launchpad')

    def test_parent_gets_newer(self):
        # When a new source package is uploaded to the parent distroseries,
        # a job is created that updates the relevant DSD.
        derived_series = self.makeDerivedDistroSeries()
        source_package_name = self.factory.makeSourcePackageName()
        self.createPublication(
            source_package_name, ['1.0-1derived1', '1.0-1'], derived_series)
        self.createPublication(
            source_package_name, ['1.0-1'], derived_series.parent_series)
        # Creating the SPPHs has created jobs for us, so grab it off the
        # queue.
        jobs = find_waiting_jobs(derived_series, source_package_name)
        self.runJob(jobs[0])
        ds_diff = self.findDSD(derived_series, source_package_name)
        self.assertEqual(1, ds_diff.count())
        self.assertEqual('1.0-1', ds_diff[0].parent_source_version)
        self.assertEqual('1.0-1derived1', ds_diff[0].source_version)
        self.assertEqual('1.0-1', ds_diff[0].base_version)
        # Now create a 1.0-2 upload to the parent.
        self.createPublication(
            source_package_name, ['1.0-2', '1.0-1'],
            derived_series.parent_series)
        jobs = find_waiting_jobs(derived_series, source_package_name)
        self.runJob(jobs[0])
        # And the DSD we have a hold of will have updated.
        self.assertEqual('1.0-2', ds_diff[0].parent_source_version)
        self.assertEqual('1.0-1derived1', ds_diff[0].source_version)
        self.assertEqual('1.0-1', ds_diff[0].base_version)

    def test_child_gets_newer(self):
        # When a new source is uploaded to the child distroseries, the DSD is
        # updated.
        derived_series = self.makeDerivedDistroSeries()
        source_package_name = self.factory.makeSourcePackageName()
        self.createPublication(
            source_package_name, ['1.0-1'], derived_series)
        self.createPublication(
            source_package_name, ['1.0-1'], derived_series.parent_series)
        jobs = find_waiting_jobs(derived_series, source_package_name)
        self.runJob(jobs[0])
        ds_diff = self.findDSD(derived_series, source_package_name)
        self.assertEqual(
            DistroSeriesDifferenceStatus.RESOLVED, ds_diff[0].status)
        self.createPublication(
            source_package_name, ['2.0-0derived1', '1.0-1'], derived_series)
        jobs = find_waiting_jobs(derived_series, source_package_name)
        self.runJob(jobs[0])
        self.assertEqual(
            DistroSeriesDifferenceStatus.NEEDS_ATTENTION, ds_diff[0].status)
        self.assertEqual('1.0-1', ds_diff[0].base_version)

    def test_child_is_synced(self):
        # If the source package gets 'synced' to the child from the parent,
        # the job correctly updates the DSD.
        derived_series = self.makeDerivedDistroSeries()
        source_package_name = self.factory.makeSourcePackageName()
        self.createPublication(
            source_package_name, ['1.0-1derived1', '1.0-1'], derived_series)
        self.createPublication(
            source_package_name, ['1.0-2', '1.0-1'],
            derived_series.parent_series)
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
        derived_series = self.makeDerivedDistroSeries()
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
        derived_series = self.makeDerivedDistroSeries()
        source_package_name = self.factory.makeSourcePackageName()
        self.createPublication(
            source_package_name, ['1.0-1'],
            derived_series.parent_series)
        jobs = find_waiting_jobs(derived_series, source_package_name)
        self.runJob(jobs[0])
        ds_diff = self.findDSD(derived_series, source_package_name)
        self.assertEqual(
            DistroSeriesDifferenceType.MISSING_FROM_DERIVED_SERIES,
            ds_diff[0].difference_type)

    def test_deleted_in_parent(self):
        # If a source package is deleted in the parent, a job is created, and
        # the DSD is updated correctly.
        derived_series = self.makeDerivedDistroSeries()
        source_package_name = self.factory.makeSourcePackageName()
        self.createPublication(
            source_package_name, ['1.0-1'], derived_series)
        spph = self.createPublication(
            source_package_name, ['1.0-1'], derived_series.parent_series)
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
        derived_series = self.makeDerivedDistroSeries()
        source_package_name = self.factory.makeSourcePackageName()
        spph = self.createPublication(
            source_package_name, ['1.0-1'], derived_series)
        self.createPublication(
            source_package_name, ['1.0-1'], derived_series.parent_series)
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
        derived_series = self.makeDerivedDistroSeries()
        source_package_name = self.factory.makeSourcePackageName()
        ppa = self.factory.makeArchive()
        self.createPublication(
            source_package_name, ['1.0-1'], derived_series, ppa)
        jobs = find_waiting_jobs(derived_series, source_package_name)
        self.assertEqual(0, jobs.count())

    def test_no_job_for_PPA_with_deleted_source(self):
        # If a source package is deleted from a PPA, no job is created.
        derived_series = self.makeDerivedDistroSeries()
        source_package_name = self.factory.makeSourcePackageName()
        ppa = self.factory.makeArchive()
        spph = self.createPublication(
            source_package_name, ['1.0-1'], derived_series, ppa)
        spph.requestDeletion(ppa.owner)
        jobs = find_waiting_jobs(derived_series, source_package_name)
        self.assertEqual(0, jobs.count())

    def test_update_deletes_diffs(self):
        # When a DSD is updated, the diffs are invalidated.
        derived_series = self.makeDerivedDistroSeries()
        source_package_name = self.factory.makeSourcePackageName()
        self.createPublication(
            source_package_name, ['1.0-1derived1', '1.0-1'], derived_series)
        self.createPublication(
            source_package_name, ['1.0-2', '1.0-1'],
            derived_series.parent_series)
        spr = self.factory.makeSourcePackageRelease(
            sourcepackagename=source_package_name, version='1.0-1')
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagerelease=spr,
            archive=derived_series.parent_series.main_archive,
            distroseries=derived_series.parent_series,
            status=PackagePublishingStatus.SUPERSEDED)
        jobs = find_waiting_jobs(derived_series, source_package_name)
        self.runJob(jobs[0])
        ds_diff = self.findDSD(derived_series, source_package_name)
        ds_diff[0].requestPackageDiffs(self.factory.makePerson())
        self.assertIsNot(None, ds_diff[0].package_diff)
        self.assertIsNot(None, ds_diff[0].parent_package_diff)
        self.createPublication(
            source_package_name, ['1.0-3', '1.0-2', '1.0-1'],
            derived_series.parent_series)
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
        derived_series = self.factory.makeDistroSeries(
            previous_series=self.factory.makeDistroSeries())
        packages = dict(
            (user, self.factory.makeSourcePackageName())
            for user in script_users)
        transaction.commit()
        for user in script_users:
            self.layer.switchDbUser(user)
            try:
                create_job(derived_series, packages[user])
            except ProgrammingError, e:
                self.assertTrue(
                    False,
                    "Database role %s was unable to create a job.  "
                    "Error was: %s" % (user, e))

        # The test is that we get here without exceptions.
        pass
