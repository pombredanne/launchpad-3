# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for sync package jobs."""

from testtools.content import text_content
import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.testing import LaunchpadZopelessLayer
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.features.testing import FeatureFixture
from lp.services.job.interfaces.job import JobStatus
from lp.registry.interfaces.sourcepackage import SourcePackageUrgency
from lp.soyuz.enums import (
    ArchivePurpose,
    SourcePackageFormat,
    )
from lp.soyuz.model.distroseriesdifferencejob import (
    FEATURE_FLAG_ENABLE_MODULE,
    )
from lp.soyuz.interfaces.archive import CannotCopy
from lp.soyuz.interfaces.packagecopyjob import (
    IPackageCopyJob,
    IPlainPackageCopyJobSource,
    )
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.interfaces.sourcepackageformat import (
    ISourcePackageFormatSelectionSet,
    )
from lp.soyuz.model.packagecopyjob import specify_dsd_package
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    run_script,
    TestCaseWithFactory,
    )


class PlainPackageCopyJobTests(TestCaseWithFactory):
    """Test case for PlainPackageCopyJob."""

    layer = LaunchpadZopelessLayer
    # XXX: GavinPanella 2011-04-20 bug=770297: The sync_packages database
    # user should be renamed to copy_packages.
    dbuser = 'sync_packages'

    def makeJob(self, dsd):
        """Create a `PlainPackageCopyJob` that would resolve `dsd`."""
        source_packages = [specify_dsd_package(dsd)]
        source_archive = dsd.parent_series.main_archive
        target_archive = dsd.derived_series.main_archive
        target_distroseries = dsd.derived_series
        target_pocket = self.factory.getAnyPocket()
        return getUtility(IPlainPackageCopyJobSource).create(
            source_packages, source_archive, target_archive,
            target_distroseries, target_pocket)

    def runJob(self, job):
        """Helper to switch to the right DB user and run the job."""
        self.layer.txn.commit()
        self.layer.switchDbUser(self.dbuser)
        job.run()

    def test_create(self):
        # A PackageCopyJob can be created and stores its arguments.
        distroseries = self.factory.makeDistroSeries()
        archive1 = self.factory.makeArchive(distroseries.distribution)
        archive2 = self.factory.makeArchive(distroseries.distribution)
        source = getUtility(IPlainPackageCopyJobSource)
        job = source.create(
            source_packages=[("foo", "1.0-1"), ("bar", "2.4")],
            source_archive=archive1, target_archive=archive2,
            target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            include_binaries=False)
        self.assertProvides(job, IPackageCopyJob)
        self.assertEquals(archive1.id, job.source_archive_id)
        self.assertEquals(archive1, job.source_archive)
        self.assertEquals(archive2.id, job.target_archive_id)
        self.assertEquals(archive2, job.target_archive)
        self.assertEquals(distroseries, job.target_distroseries)
        self.assertEquals(PackagePublishingPocket.RELEASE, job.target_pocket)
        self.assertContentEqual(
            job.source_packages,
            [("foo", "1.0-1", None), ("bar", "2.4", None)])
        self.assertEquals(False, job.include_binaries)

    def test_getActiveJobs(self):
        # getActiveJobs() can retrieve all active jobs for an archive.
        distroseries = self.factory.makeDistroSeries()
        archive1 = self.factory.makeArchive(distroseries.distribution)
        archive2 = self.factory.makeArchive(distroseries.distribution)
        source = getUtility(IPlainPackageCopyJobSource)
        job = source.create(
            source_packages=[("foo", "1.0-1")], source_archive=archive1,
            target_archive=archive2, target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            include_binaries=False)
        self.assertContentEqual([job], source.getActiveJobs(archive2))

    def test_getActiveJobs_gets_oldest_first(self):
        # getActiveJobs returns the oldest available job first.
        dsd = self.factory.makeDistroSeriesDifference()
        target_archive = dsd.derived_series.main_archive
        jobs = [self.makeJob(dsd) for counter in xrange(2)]
        source = getUtility(IPlainPackageCopyJobSource)
        self.assertEqual(jobs[0], source.getActiveJobs(target_archive)[0])

    def test_getActiveJobs_only_returns_waiting_jobs(self):
        # getActiveJobs ignores jobs that aren't in the WAITING state.
        job = self.makeJob(self.factory.makeDistroSeriesDifference())
        removeSecurityProxy(job).job._status = JobStatus.RUNNING
        source = getUtility(IPlainPackageCopyJobSource)
        self.assertContentEqual([], source.getActiveJobs(job.target_archive))

    def test_run_unknown_package(self):
        # A job properly records failure.
        distroseries = self.factory.makeDistroSeries()
        archive1 = self.factory.makeArchive(distroseries.distribution)
        archive2 = self.factory.makeArchive(distroseries.distribution)
        source = getUtility(IPlainPackageCopyJobSource)
        job = source.create(
            source_packages=[("foo", "1.0-1")], source_archive=archive1,
            target_archive=archive2, target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            include_binaries=False)
        self.assertRaises(CannotCopy, self.runJob, job)

    def test_target_ppa_non_release_pocket(self):
        # When copying to a PPA archive the target must be the release pocket.
        distroseries = self.factory.makeDistroSeries()
        archive1 = self.factory.makeArchive(distroseries.distribution)
        archive2 = self.factory.makeArchive(distroseries.distribution)
        source = getUtility(IPlainPackageCopyJobSource)
        job = source.create(
            source_packages=[], source_archive=archive1,
            target_archive=archive2, target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.UPDATES,
            include_binaries=False)
        self.assertRaises(CannotCopy, self.runJob, job)

    def test_run(self):
        # A proper test run synchronizes packages.

        # Turn on DSD jobs.
        self.useFixture(FeatureFixture({FEATURE_FLAG_ENABLE_MODULE: 'on'}))

        publisher = SoyuzTestPublisher()
        publisher.prepareBreezyAutotest()
        distroseries = publisher.breezy_autotest

        # Synchronise from breezy-autotest to a brand new distro derived
        # from breezy.
        breezy_archive = self.factory.makeArchive(
            distroseries.distribution, purpose=ArchivePurpose.PRIMARY)
        dsp = self.factory.makeDistroSeriesParent(parent_series=distroseries)
        target_series = dsp.derived_series
        target_archive = self.factory.makeArchive(
            target_series.distribution, purpose=ArchivePurpose.PRIMARY)
        getUtility(ISourcePackageFormatSelectionSet).add(
            target_series, SourcePackageFormat.FORMAT_1_0)

        source_package = publisher.getPubSource(
            distroseries=distroseries, sourcename="libc",
            version="2.8-1", status=PackagePublishingStatus.PUBLISHED,
            archive=breezy_archive)

        source = getUtility(IPlainPackageCopyJobSource)
        job = source.create(
            source_packages=[("libc", "2.8-1")], source_archive=breezy_archive,
            target_archive=target_archive, target_distroseries=target_series,
            target_pocket=PackagePublishingPocket.RELEASE,
            include_binaries=False)
        self.assertContentEqual(
            job.source_packages, [("libc", "2.8-1", source_package)])

        # Make sure everything hits the database, switching db users
        # aborts.
        transaction.commit()
        self.layer.switchDbUser(self.dbuser)
        job.run()

        published_sources = target_archive.getPublishedSources()
        spr = published_sources.one().sourcepackagerelease
        self.assertEquals("libc", spr.name)
        self.assertEquals("2.8-1", spr.version)

        # Switch back to a db user that has permission to clean up
        # featureflag.
        self.layer.switchDbUser('launchpad_main')

    def test_getOopsVars(self):
        distroseries = self.factory.makeDistroSeries()
        archive1 = self.factory.makeArchive(distroseries.distribution)
        archive2 = self.factory.makeArchive(distroseries.distribution)
        source = getUtility(IPlainPackageCopyJobSource)
        job = source.create(
            source_packages=[("foo", "1.0-1")], source_archive=archive1,
            target_archive=archive2, target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            include_binaries=False)
        oops_vars = job.getOopsVars()
        naked_job = removeSecurityProxy(job)
        self.assertIn(
            ('source_archive_id', archive1.id), oops_vars)
        self.assertIn(
            ('target_archive_id', archive2.id), oops_vars)
        self.assertIn(
            ('target_distroseries_id', distroseries.id), oops_vars)
        self.assertIn(
            ('package_copy_job_id', naked_job.context.id), oops_vars)
        self.assertIn(
            ('package_copy_job_type', naked_job.context.job_type.title),
            oops_vars)

    def test_smoke(self):
        publisher = SoyuzTestPublisher()
        publisher.prepareBreezyAutotest()
        distroseries = publisher.breezy_autotest
        archive1 = self.factory.makeArchive(distroseries.distribution)
        archive2 = self.factory.makeArchive(distroseries.distribution)
        publisher.getPubSource(
            distroseries=distroseries, sourcename="libc",
            version="2.8-1", status=PackagePublishingStatus.PUBLISHED,
            archive=archive1)
        getUtility(IPlainPackageCopyJobSource).create(
            source_packages=[("libc", "2.8-1")], source_archive=archive1,
            target_archive=archive2, target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            include_binaries=False)
        transaction.commit()

        out, err, exit_code = run_script(
            "LP_DEBUG_SQL=1 cronscripts/process-job-source.py -vv %s" % (
                IPlainPackageCopyJobSource.getName()))

        self.addDetail("stdout", text_content(out))
        self.addDetail("stderr", text_content(err))

        self.assertEqual(0, exit_code)
        copied_source_package = archive2.getPublishedSources(
            name="libc", version="2.8-1", exact_match=True).first()
        self.assertIsNot(copied_source_package, None)

    def test___repr__(self):
        distroseries = self.factory.makeDistroSeries()
        archive1 = self.factory.makeArchive(distroseries.distribution)
        archive2 = self.factory.makeArchive(distroseries.distribution)
        source = getUtility(IPlainPackageCopyJobSource)
        job = source.create(
            source_packages=[("foo", "1.0-1"), ("bar", "2.4")],
            source_archive=archive1, target_archive=archive2,
            target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            include_binaries=True)
        self.assertEqual(
            ("<PlainPackageCopyJob to copy 2 package(s) from "
             "{distroseries.distribution.name}/{archive1.name} to "
             "{distroseries.distribution.name}/{archive2.name}, "
             "RELEASE pocket, in {distroseries.distribution.name} "
             "{distroseries.name}, including binaries>").format(
                distroseries=distroseries, archive1=archive1,
                archive2=archive2),
            repr(job))

    def test_getPendingJobsPerPackage_finds_jobs(self):
        # getPendingJobsPerPackage finds jobs, and the packages they
        # belong to.
        dsd = self.factory.makeDistroSeriesDifference()
        job = self.makeJob(dsd)
        job_source = getUtility(IPlainPackageCopyJobSource)
        self.assertEqual(
            {specify_dsd_package(dsd): job},
            job_source.getPendingJobsPerPackage(dsd.derived_series))

    def test_getPendingJobsPerPackage_ignores_other_distroseries(self):
        # getPendingJobsPerPackage only looks for jobs on the indicated
        # distroseries.
        dsd = self.factory.makeDistroSeriesDifference()
        self.makeJob(dsd)
        other_series = self.factory.makeDistroSeries()
        job_source = getUtility(IPlainPackageCopyJobSource)
        self.assertEqual(
            {}, job_source.getPendingJobsPerPackage(other_series))

    def test_getPendingJobsPerPackage_only_returns_pending_jobs(self):
        # getPendingJobsPerPackage ignores jobs that have already been
        # run.
        dsd = self.factory.makeDistroSeriesDifference()
        package = specify_dsd_package(dsd)
        job = self.makeJob(dsd)
        job_source = getUtility(IPlainPackageCopyJobSource)
        found_by_state = {}
        for status in JobStatus.items:
            removeSecurityProxy(job).job._status = status
            result = job_source.getPendingJobsPerPackage(dsd.derived_series)
            if len(result) > 0:
                found_by_state[status] = result[package]
        expected = {
            JobStatus.WAITING: job,
            JobStatus.RUNNING: job,
            JobStatus.SUSPENDED: job,
        }
        self.assertEqual(expected, found_by_state)

    def test_getPendingJobsPerPackage_distinguishes_jobs(self):
        # getPendingJobsPerPackage associates the right job with the
        # right package.
        derived_series = self.factory.makeDistroSeries()
        dsds = [
            self.factory.makeDistroSeriesDifference(
                derived_series=derived_series)
            for counter in xrange(2)]
        jobs = map(self.makeJob, dsds)
        job_source = getUtility(IPlainPackageCopyJobSource)
        self.assertEqual(
            dict(zip(map(specify_dsd_package, dsds), jobs)),
            job_source.getPendingJobsPerPackage(derived_series))

    def test_getPendingJobsPerPackage_picks_oldest_job_for_dsd(self):
        # If there are multiple jobs for one package,
        # getPendingJobsPerPackage picks the oldest.
        dsd = self.factory.makeDistroSeriesDifference()
        jobs = [self.makeJob(dsd) for counter in xrange(2)]
        job_source = getUtility(IPlainPackageCopyJobSource)
        self.assertEqual(
            {specify_dsd_package(dsd): jobs[0]},
            job_source.getPendingJobsPerPackage(dsd.derived_series))

    def test_getPendingJobsPerPackage_ignores_dsds_without_jobs(self):
        # getPendingJobsPerPackage produces no dict entry for packages
        # that have no pending jobs, even if they do have DSDs.
        dsd = self.factory.makeDistroSeriesDifference()
        job_source = getUtility(IPlainPackageCopyJobSource)
        self.assertEqual(
            {}, job_source.getPendingJobsPerPackage(dsd.derived_series))

    def test_copying_to_main_archive_ancestry_overrides(self):
        # The job will complete right away for auto-approved copies to a
        # main archive and apply any ancestry overrides.
        publisher = SoyuzTestPublisher()
        publisher.prepareBreezyAutotest()
        distroseries = publisher.breezy_autotest

        target_archive = self.factory.makeArchive(
            distroseries.distribution, purpose=ArchivePurpose.PRIMARY)
        source_archive = self.factory.makeArchive()
        #getUtility(ISourcePackageFormatSelectionSet).add(
        #    target_series, SourcePackageFormat.FORMAT_1_0)

        # Publish a package in the source archive with some overridable
        # properties set to known values.
        source_package = publisher.getPubSource(
            distroseries=distroseries, sourcename="libc",
            component='universe', section='web',
            version="2.8-1", status=PackagePublishingStatus.PUBLISHED,
            archive=source_archive)

        # Now put the same named package in the target archive with
        # different override values.
        ancestry_package = publisher.getPubSource(
            distroseries=distroseries, sourcename="libc",
            component='restricted', section='games',
            version="2.8-0", status=PackagePublishingStatus.PUBLISHED,
            archive=target_archive)

        # Now, run the copy job, which should auto-approve the copy and
        # override the package with the existing values in the
        # target_archive.

        source = getUtility(IPlainPackageCopyJobSource)
        job = source.create(
            source_packages=[("libc", "2.8-1")],
            source_archive=source_archive,
            target_archive=target_archive,
            target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            include_binaries=False)

        self.runJob(job)

        new_publication = target_archive.getPublishedSources(
            name='libc', version='2.8-1').one()
        self.assertEqual('restricted', new_publication.component.name)
        self.assertEqual('games', new_publication.section.name)
