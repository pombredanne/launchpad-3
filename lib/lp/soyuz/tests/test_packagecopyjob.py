# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for sync package jobs."""

from testtools.content import text_content
from testtools.matchers import (
    Equals,
    MatchesStructure,
    )
import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.testing import LaunchpadZopelessLayer
from lp.registry.model.distroseriesdifferencecomment import (
    DistroSeriesDifferenceComment,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.features.testing import FeatureFixture
from lp.services.job.interfaces.job import JobStatus
from lp.soyuz.adapters.overrides import SourceOverride
from lp.soyuz.enums import (
    ArchivePurpose,
    SourcePackageFormat,
    )
from lp.soyuz.model.distroseriesdifferencejob import (
    FEATURE_FLAG_ENABLE_MODULE,
    )
from lp.soyuz.interfaces.archive import CannotCopy
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.packagecopyjob import (
    IPackageCopyJob,
    IPlainPackageCopyJobSource,
    )
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.interfaces.section import ISectionSet
from lp.soyuz.interfaces.sourcepackageformat import (
    ISourcePackageFormatSelectionSet,
    )
from lp.soyuz.model.packagecopyjob import specify_dsd_package
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    run_script,
    TestCaseWithFactory,
    )
from lp.testing.fakemethod import FakeMethod


def get_dsd_comments(dsd):
    """Retrieve `DistroSeriesDifferenceComment`s for `dsd`."""
    return IStore(dsd).find(
        DistroSeriesDifferenceComment,
        DistroSeriesDifferenceComment.distro_series_difference == dsd)


class LocalTestHelper:
    """Put test helpers that want to be in the test classes here."""

    def makeJob(self, dsd=None):
        """Create a `PlainPackageCopyJob` that would resolve `dsd`."""
        if dsd is None:
            dsd = self.factory.makeDistroSeriesDifference()
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
        self.layer.switchDbUser('sync_packages')
        job.run()


class PlainPackageCopyJobTests(TestCaseWithFactory, LocalTestHelper):
    """Test case for PlainPackageCopyJob."""

    layer = LaunchpadZopelessLayer

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
        job = self.makeJob()
        removeSecurityProxy(job).job._status = JobStatus.RUNNING
        source = getUtility(IPlainPackageCopyJobSource)
        self.assertContentEqual([], source.getActiveJobs(job.target_archive))

    def test_run_raises_errors(self):
        # A job reports unexpected errors as exceptions.
        class Boom(Exception):
            pass

        job = self.makeJob()
        removeSecurityProxy(job).attemptCopy = FakeMethod(failure=Boom())

        self.assertRaises(Boom, job.run)

    def test_run_posts_copy_failure_as_comment(self):
        # If the job fails with a CannotCopy exception, it swallows the
        # exception and posts a DistroSeriesDifferenceComment with the
        # failure message.
        dsd = self.factory.makeDistroSeriesDifference()
        self.factory.makeArchive(distribution=dsd.derived_series.distribution)
        job = self.makeJob(dsd)
        removeSecurityProxy(job).attemptCopy = FakeMethod(
            failure=CannotCopy("Server meltdown"))

        # The job's error handling will abort, so commit the objects we
        # created as would have happened in real life.
        transaction.commit()

        job.run()

        self.assertEqual(
            ["Server meltdown"],
            [comment.body_text for comment in get_dsd_comments(dsd)])

    def test_run_cannot_copy_unknown_package(self):
        # Attempting to copy an unknown package is reported as a
        # failure.
        distroseries = self.factory.makeDistroSeries()
        archive1 = self.factory.makeArchive(distroseries.distribution)
        archive2 = self.factory.makeArchive(distroseries.distribution)
        job_source = getUtility(IPlainPackageCopyJobSource)
        job = job_source.create(
            source_packages=[("foo", "1.0-1")], source_archive=archive1,
            target_archive=archive2, target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            include_binaries=False)
        naked_job = removeSecurityProxy(job)
        naked_job.reportFailure = FakeMethod()

        job.run()

        self.assertEqual(1, naked_job.reportFailure.call_count)

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

        naked_job = removeSecurityProxy(job)
        naked_job.reportFailure = FakeMethod()

        job.run()

        self.assertEqual(1, naked_job.reportFailure.call_count)

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
            source_packages=[("libc", "2.8-1")],
            source_archive=breezy_archive, target_archive=target_archive,
            target_distroseries=target_series,
            target_pocket=PackagePublishingPocket.RELEASE,
            include_binaries=False)
        self.assertContentEqual(
            job.source_packages, [("libc", "2.8-1", source_package)])

        # Make sure everything hits the database, switching db users
        # aborts.
        transaction.commit()
        # XXX: GavinPanella 2011-04-20 bug=770297: The sync_packages database
        # user should be renamed to copy_packages.
        self.layer.switchDbUser('sync_packages')
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
        self.makeJob()
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

    def test_findMatchingDSDs_matches_all_DSDs_for_job(self):
        # findMatchingDSDs finds matching DSDs for any of the packages
        # in the job.
        dsd = self.factory.makeDistroSeriesDifference()
        naked_job = removeSecurityProxy(self.makeJob(dsd))
        self.assertContentEqual([dsd], naked_job.findMatchingDSDs())

    def test_findMatchingDSDs_ignores_other_source_series(self):
        # findMatchingDSDs tries to ignore DSDs that are for different
        # parent series than the job's source series.  (This can't be
        # done with perfect precision because the job doesn't keep track
        # of source distroseries, but in practice it should be good
        # enough).
        dsd = self.factory.makeDistroSeriesDifference()
        naked_job = removeSecurityProxy(self.makeJob(dsd))

        # If the dsd differs only in parent series, that's enough to
        # make it a non-match.
        removeSecurityProxy(dsd).parent_series = (
            self.factory.makeDistroSeries())

        self.assertContentEqual([], naked_job.findMatchingDSDs())

    def test_findMatchingDSDs_ignores_other_packages(self):
        # findMatchingDSDs does not return DSDs that are similar to the
        # information in the job, but are for different packages.
        dsd = self.factory.makeDistroSeriesDifference()
        self.factory.makeDistroSeriesDifference(
            derived_series=dsd.derived_series,
            parent_series=dsd.parent_series)
        naked_job = removeSecurityProxy(self.makeJob(dsd))
        self.assertContentEqual([dsd], naked_job.findMatchingDSDs())

    def test_addSourceOverride(self):
        # Test the addOverride method which adds an ISourceOverride to the
        # metadata.
        name = self.factory.makeSourcePackageName()
        component = self.factory.makeComponent()
        section=self.factory.makeSection()
        pcj = self.factory.makePlainPackageCopyJob()
        self.layer.txn.commit()
        self.layer.switchDbUser('sync_packages')

        override = SourceOverride(
            source_package_name=name,
            component=component,
            section=section)
        pcj.addSourceOverride(override)

        metadata_component = getUtility(
            IComponentSet)[pcj.metadata["component_override"]]
        metadata_section = getUtility(
            ISectionSet)[pcj.metadata["section_override"]]
        matcher = MatchesStructure(
            component=Equals(metadata_component),
            section=Equals(metadata_section))
        self.assertThat(override, matcher)

    def test_getSourceOverride(self):
        # Test the getSourceOverride which gets an ISourceOverride from
        # the metadata.
        name = self.factory.makeSourcePackageName()
        component = self.factory.makeComponent()
        section=self.factory.makeSection()
        pcj = self.factory.makePlainPackageCopyJob(
            package_name=name.name, package_version="1.0")
        self.layer.txn.commit()
        self.layer.switchDbUser('sync_packages')

        override = SourceOverride(
            source_package_name=name,
            component=component,
            section=section)
        pcj.addSourceOverride(override)

        self.assertEqual(override, pcj.getSourceOverride())


class TestPlainPackageCopyJobPrivileges(TestCaseWithFactory, LocalTestHelper):
    """Test that `PlainPackageCopyJob` has the privileges it needs.

    This test looks for errors, not failures.  It's here only to see that
    these operations don't run into any privilege limitations.
    """

    layer = LaunchpadZopelessLayer

    def test_findMatchingDSDs(self):
        job = self.makeJob()
        transaction.commit()
        self.layer.switchDbUser(config.IPlainPackageCopyJobSource.dbuser)
        removeSecurityProxy(job).findMatchingDSDs()

    def test_reportFailure(self):
        job = self.makeJob()
        transaction.commit()
        self.layer.switchDbUser(config.IPlainPackageCopyJobSource.dbuser)
        removeSecurityProxy(job).reportFailure(CannotCopy("Mommy it hurts"))
