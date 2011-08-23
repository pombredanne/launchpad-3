# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for sync package jobs."""

import operator

from storm.store import Store
from testtools.content import text_content
from testtools.matchers import MatchesStructure
import transaction
from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing import (
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.registry.model.distroseriesdifferencecomment import (
    DistroSeriesDifferenceComment,
    )
from lp.services.features.testing import FeatureFixture
from lp.services.job.interfaces.job import (
    JobStatus,
    SuspendJobException,
    )
from lp.soyuz.adapters.overrides import SourceOverride
from lp.soyuz.enums import (
    ArchivePurpose,
    PackageCopyPolicy,
    PackageUploadStatus,
    SourcePackageFormat,
    )
from lp.soyuz.interfaces.archive import CannotCopy
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.packagecopyjob import (
    IPackageCopyJob,
    IPackageCopyJobSource,
    IPlainPackageCopyJob,
    IPlainPackageCopyJobSource,
    )
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.interfaces.queue import IPackageUploadSet
from lp.soyuz.interfaces.section import ISectionSet
from lp.soyuz.interfaces.sourcepackageformat import (
    ISourcePackageFormatSelectionSet,
    )
from lp.soyuz.model.distroseriesdifferencejob import (
    FEATURE_FLAG_ENABLE_MODULE,
    )
from lp.soyuz.model.packagecopyjob import PackageCopyJob
from lp.soyuz.model.queue import PackageUpload
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    person_logged_in,
    run_script,
    TestCaseWithFactory,
    )
from lp.testing.fakemethod import FakeMethod
from lp.testing.mail_helpers import pop_notifications
from lp.testing.matchers import Provides


def get_dsd_comments(dsd):
    """Retrieve `DistroSeriesDifferenceComment`s for `dsd`."""
    return IStore(dsd).find(
        DistroSeriesDifferenceComment,
        DistroSeriesDifferenceComment.distro_series_difference == dsd)


class LocalTestHelper:
    """Put test helpers that want to be in the test classes here."""

    dbuser = config.IPlainPackageCopyJobSource.dbuser

    def makeJob(self, dsd=None, **kwargs):
        """Create a `PlainPackageCopyJob` that would resolve `dsd`."""
        if dsd is None:
            dsd = self.factory.makeDistroSeriesDifference()
        source_archive = dsd.parent_series.main_archive
        target_archive = dsd.derived_series.main_archive
        target_distroseries = dsd.derived_series
        target_pocket = self.factory.getAnyPocket()
        requester = self.factory.makePerson()
        return getUtility(IPlainPackageCopyJobSource).create(
            dsd.source_package_name.name, source_archive, target_archive,
            target_distroseries, target_pocket, requester=requester,
            package_version=dsd.parent_source_version, **kwargs)

    def runJob(self, job):
        """Helper to switch to the right DB user and run the job."""
        # We are basically mimicking the job runner here.
        self.layer.txn.commit()
        self.layer.switchDbUser(self.dbuser)
        # Set the state to RUNNING.
        job.start()
        # Commit the RUNNING state.
        self.layer.txn.commit()
        try:
            job.run()
        except SuspendJobException:
            # Re-raise this one as many tests check for its presence.
            raise
        except:
            transaction.abort()
            job.fail()
        else:
            job.complete()


class PlainPackageCopyJobTests(TestCaseWithFactory, LocalTestHelper):
    """Test case for PlainPackageCopyJob."""

    layer = LaunchpadZopelessLayer

    def test_job_implements_IPlainPackageCopyJob(self):
        job = self.makeJob()
        self.assertTrue(verifyObject(IPlainPackageCopyJob, job))

    def test_job_source_implements_IPlainPackageCopyJobSource(self):
        job_source = getUtility(IPlainPackageCopyJobSource)
        self.assertTrue(verifyObject(IPlainPackageCopyJobSource, job_source))

    def test_create(self):
        # A PackageCopyJob can be created and stores its arguments.
        distroseries = self.factory.makeDistroSeries()
        archive1 = self.factory.makeArchive(distroseries.distribution)
        archive2 = self.factory.makeArchive(distroseries.distribution)
        requester = self.factory.makePerson()
        source = getUtility(IPlainPackageCopyJobSource)
        job = source.create(
            package_name="foo", source_archive=archive1,
            target_archive=archive2, target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            package_version="1.0-1", include_binaries=False,
            copy_policy=PackageCopyPolicy.MASS_SYNC,
            requester=requester)
        self.assertProvides(job, IPackageCopyJob)
        self.assertEquals(archive1.id, job.source_archive_id)
        self.assertEquals(archive1, job.source_archive)
        self.assertEquals(archive2.id, job.target_archive_id)
        self.assertEquals(archive2, job.target_archive)
        self.assertEquals(distroseries, job.target_distroseries)
        self.assertEquals(PackagePublishingPocket.RELEASE, job.target_pocket)
        self.assertEqual("foo", job.package_name)
        self.assertEqual("1.0-1", job.package_version)
        self.assertEquals(False, job.include_binaries)
        self.assertEquals(PackageCopyPolicy.MASS_SYNC, job.copy_policy)
        self.assertEqual(requester, job.requester)

    def test_createMultiple_creates_one_job_per_copy(self):
        mother = self.factory.makeDistroSeriesParent()
        derived_series = mother.derived_series
        father = self.factory.makeDistroSeriesParent(
            derived_series=derived_series)
        mother_package = self.factory.makeSourcePackageName()
        father_package = self.factory.makeSourcePackageName()
        requester = self.factory.makePerson()
        job_source = getUtility(IPlainPackageCopyJobSource)
        copy_tasks = [
            (
                mother_package.name,
                "1.5mother1",
                mother.parent_series.main_archive,
                derived_series.main_archive,
                PackagePublishingPocket.RELEASE,
                ),
            (
                father_package.name,
                "0.9father1",
                father.parent_series.main_archive,
                derived_series.main_archive,
                PackagePublishingPocket.UPDATES,
                ),
            ]
        job_ids = list(
            job_source.createMultiple(mother.derived_series, copy_tasks,
                                      requester))
        jobs = list(job_source.getActiveJobs(derived_series.main_archive))
        self.assertContentEqual(job_ids, [job.id for job in jobs])
        self.assertEqual(len(copy_tasks), len(set([job.job for job in jobs])))
        # Get jobs into the same order as copy_tasks, for ease of
        # comparison.
        if jobs[0].package_name != mother_package.name:
            jobs = reversed(jobs)
        requested_copies = [
            (
                job.package_name,
                job.package_version,
                job.source_archive,
                job.target_archive,
                job.target_pocket,
                )
            for job in jobs]
        self.assertEqual(copy_tasks, requested_copies)

        # The passed requester should be the same on all jobs.
        actual_requester = set(job.requester for job in jobs)
        self.assertEqual(1, len(actual_requester))
        self.assertEqual(requester, jobs[0].requester)

    def test_getActiveJobs(self):
        # getActiveJobs() can retrieve all active jobs for an archive.
        distroseries = self.factory.makeDistroSeries()
        archive1 = self.factory.makeArchive(distroseries.distribution)
        archive2 = self.factory.makeArchive(distroseries.distribution)
        source = getUtility(IPlainPackageCopyJobSource)
        requester = self.factory.makePerson()
        job = source.create(
            package_name="foo", source_archive=archive1,
            target_archive=archive2, target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            package_version="1.0-1", include_binaries=False,
            requester=requester)
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
        requester = self.factory.makePerson()
        job_source = getUtility(IPlainPackageCopyJobSource)
        job = job_source.create(
            package_name="foo", source_archive=archive1,
            target_archive=archive2, target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            package_version="1.0-1", include_binaries=False,
            requester=requester)
        naked_job = removeSecurityProxy(job)
        naked_job.reportFailure = FakeMethod()

        job.run()

        self.assertEqual(1, naked_job.reportFailure.call_count)

    def test_target_ppa_non_release_pocket(self):
        # When copying to a PPA archive the target must be the release pocket.
        distroseries = self.factory.makeDistroSeries()
        package = self.factory.makeSourcePackageName()
        archive1 = self.factory.makeArchive(distroseries.distribution)
        archive2 = self.factory.makeArchive(distroseries.distribution)
        requester = self.factory.makePerson()
        source = getUtility(IPlainPackageCopyJobSource)
        job = source.create(
            package_name=package.name, source_archive=archive1,
            target_archive=archive2, target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.UPDATES,
            include_binaries=False, package_version='1.0',
            requester=requester)

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

        publisher.getPubSource(
            distroseries=distroseries, sourcename="libc",
            version="2.8-1", status=PackagePublishingStatus.PUBLISHED,
            archive=breezy_archive)
        # The target archive needs ancestry so the package is
        # auto-accepted.
        publisher.getPubSource(
            distroseries=target_series, sourcename="libc",
            version="2.8-0", status=PackagePublishingStatus.PUBLISHED,
            archive=target_archive)

        source = getUtility(IPlainPackageCopyJobSource)
        requester = self.factory.makePerson()
        with person_logged_in(target_archive.owner):
            target_archive.newComponentUploader(requester, "main")
        job = source.create(
            package_name="libc",
            source_archive=breezy_archive, target_archive=target_archive,
            target_distroseries=target_series,
            target_pocket=PackagePublishingPocket.RELEASE,
            package_version="2.8-1", include_binaries=False,
            requester=requester)
        self.assertEqual("libc", job.package_name)
        self.assertEqual("2.8-1", job.package_version)

        # Make sure everything hits the database, switching db users
        # aborts.
        transaction.commit()
        self.layer.switchDbUser(self.dbuser)
        job.run()

        published_sources = target_archive.getPublishedSources(
            name="libc", version="2.8-1")
        self.assertIsNot(None, published_sources.any())

        # The copy should have sent an email too. (see
        # soyuz/scripts/tests/test_copypackage.py for detailed
        # notification tests)
        emails = pop_notifications()
        self.assertTrue(len(emails) > 0)

        # Switch back to a db user that has permission to clean up
        # featureflag.
        self.layer.switchDbUser('launchpad_main')

    def test_getOopsVars(self):
        distroseries = self.factory.makeDistroSeries()
        archive1 = self.factory.makeArchive(distroseries.distribution)
        archive2 = self.factory.makeArchive(distroseries.distribution)
        requester = self.factory.makePerson()
        source = getUtility(IPlainPackageCopyJobSource)
        job = source.create(
            package_name="foo", source_archive=archive1,
            target_archive=archive2, target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            package_version="1.0-1", include_binaries=False,
            requester=requester)
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
        requester = self.factory.makePerson()
        publisher.getPubSource(
            distroseries=distroseries, sourcename="libc",
            version="2.8-1", status=PackagePublishingStatus.PUBLISHED,
            archive=archive1)
        getUtility(IPlainPackageCopyJobSource).create(
            package_name="libc", source_archive=archive1,
            target_archive=archive2, target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            package_version="2.8-1", include_binaries=False,
            requester=requester)
        with person_logged_in(archive2.owner):
            archive2.newComponentUploader(requester, "main")
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
        requester = self.factory.makePerson()
        source = getUtility(IPlainPackageCopyJobSource)
        job = source.create(
            package_name="foo", source_archive=archive1,
            target_archive=archive2, target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            package_version="1.0-1", include_binaries=True,
            requester=requester)
        self.assertEqual(
            ("<PlainPackageCopyJob to copy package foo from "
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
            {dsd.source_package_name.name: job},
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
        job = self.makeJob(dsd)
        job_source = getUtility(IPlainPackageCopyJobSource)
        found_by_state = {}
        for status in JobStatus.items:
            removeSecurityProxy(job).job._status = status
            result = job_source.getPendingJobsPerPackage(dsd.derived_series)
            if len(result) > 0:
                found_by_state[status] = result[dsd.source_package_name.name]
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
            dict(zip([dsd.source_package_name.name for dsd in dsds], jobs)),
            job_source.getPendingJobsPerPackage(derived_series))

    def test_getPendingJobsPerPackage_picks_oldest_job_for_dsd(self):
        # If there are multiple jobs for one package,
        # getPendingJobsPerPackage picks the oldest.
        dsd = self.factory.makeDistroSeriesDifference()
        jobs = [self.makeJob(dsd) for counter in xrange(2)]
        job_source = getUtility(IPlainPackageCopyJobSource)
        self.assertEqual(
            {dsd.source_package_name.name: jobs[0]},
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

        # Publish a package in the source archive with some overridable
        # properties set to known values.
        publisher.getPubSource(
            distroseries=distroseries, sourcename="libc",
            component='universe', section='web',
            version="2.8-1", status=PackagePublishingStatus.PUBLISHED,
            archive=source_archive)

        # Now put the same named package in the target archive with
        # different override values.
        publisher.getPubSource(
            distroseries=distroseries, sourcename="libc",
            component='restricted', section='games',
            version="2.8-0", status=PackagePublishingStatus.PUBLISHED,
            archive=target_archive)

        # Now, run the copy job, which should auto-approve the copy and
        # override the package with the existing values in the
        # target_archive.

        source = getUtility(IPlainPackageCopyJobSource)
        requester = self.factory.makePerson()
        with person_logged_in(target_archive.owner):
            target_archive.newComponentUploader(requester, "restricted")
        job = source.create(
            package_name="libc",
            package_version="2.8-1",
            source_archive=source_archive,
            target_archive=target_archive,
            target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            include_binaries=False,
            requester=requester)

        self.runJob(job)

        new_publication = target_archive.getPublishedSources(
            name='libc', version='2.8-1').one()
        self.assertEqual('restricted', new_publication.component.name)
        self.assertEqual('games', new_publication.section.name)

    def test_copying_to_ppa_archive(self):
        # Packages can be copied into PPA archives.
        publisher = SoyuzTestPublisher()
        publisher.prepareBreezyAutotest()
        distroseries = publisher.breezy_autotest

        target_archive = self.factory.makeArchive(
            distroseries.distribution, purpose=ArchivePurpose.PPA)
        source_archive = self.factory.makeArchive()

        # Publish a package in the source archive with some overridable
        # properties set to known values.
        publisher.getPubSource(
            distroseries=distroseries, sourcename="libc",
            component='universe', section='web',
            version="2.8-1", status=PackagePublishingStatus.PUBLISHED,
            archive=source_archive)

        # Now, run the copy job.
        source = getUtility(IPlainPackageCopyJobSource)
        requester = self.factory.makePerson()
        with person_logged_in(target_archive.owner):
            target_archive.newComponentUploader(requester, "main")
        job = source.create(
            package_name="libc",
            package_version="2.8-1",
            source_archive=source_archive,
            target_archive=target_archive,
            target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            include_binaries=False,
            requester=requester)

        self.runJob(job)
        self.assertEqual(JobStatus.COMPLETED, job.status)

        new_publication = target_archive.getPublishedSources(
            name='libc', version='2.8-1').one()
        self.assertEqual('main', new_publication.component.name)
        self.assertEqual('web', new_publication.section.name)

    def test_copying_to_main_archive_manual_overrides(self):
        # Test processing a packagecopyjob that has manual overrides.
        publisher = SoyuzTestPublisher()
        publisher.prepareBreezyAutotest()
        distroseries = publisher.breezy_autotest

        target_archive = self.factory.makeArchive(
            distroseries.distribution, purpose=ArchivePurpose.PRIMARY)
        source_archive = self.factory.makeArchive()

        # Publish a package in the source archive with some overridable
        # properties set to known values.
        source_package = publisher.getPubSource(
            distroseries=distroseries, sourcename="copyme",
            component='universe', section='web',
            version="2.8-1", status=PackagePublishingStatus.PUBLISHED,
            archive=source_archive)

        # Now, run the copy job, which should raise an error because
        # there's no ancestry.
        source = getUtility(IPlainPackageCopyJobSource)
        requester = self.factory.makePerson()
        with person_logged_in(target_archive.owner):
            target_archive.newComponentUploader(requester, "main")
        job = source.create(
            package_name="copyme",
            package_version="2.8-1",
            source_archive=source_archive,
            target_archive=target_archive,
            target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            include_binaries=False,
            requester=requester)

        self.assertRaises(SuspendJobException, self.runJob, job)
        # Simulate the job runner suspending after getting a
        # SuspendJobException
        job.suspend()
        self.layer.txn.commit()
        self.layer.switchDbUser("launchpad_main")

        # Add some overrides to the job.
        package = source_package.sourcepackagerelease.sourcepackagename
        restricted = getUtility(IComponentSet)['restricted']
        editors = getUtility(ISectionSet)['editors']
        override = SourceOverride(package, restricted, editors)
        job.addSourceOverride(override)

        # Accept the upload to release the job then run it.
        pu = getUtility(IPackageUploadSet).getByPackageCopyJobIDs(
            [removeSecurityProxy(job).context.id]).one()
        pu.acceptFromQueue()
        self.runJob(job)

        # The copied source should have the manual overrides, not the
        # original values.
        new_publication = target_archive.getPublishedSources(
            name='copyme', version='2.8-1').one()
        self.assertEqual('restricted', new_publication.component.name)
        self.assertEqual('editors', new_publication.section.name)

    def test_copying_to_main_archive_with_no_ancestry(self):
        # The job should suspend itself and create a packageupload with
        # a reference to the package_copy_job.
        publisher = SoyuzTestPublisher()
        publisher.prepareBreezyAutotest()
        distroseries = publisher.breezy_autotest

        target_archive = self.factory.makeArchive(
            distroseries.distribution, purpose=ArchivePurpose.PRIMARY)
        source_archive = self.factory.makeArchive()

        # Publish a package in the source archive with some overridable
        # properties set to known values.
        publisher.getPubSource(
            distroseries=distroseries, sourcename="copyme",
            component='multiverse', section='web',
            version="2.8-1", status=PackagePublishingStatus.PUBLISHED,
            archive=source_archive)

        # There is no package of the same name already in the target
        # archive.
        existing_sources = target_archive.getPublishedSources(name='copyme')
        self.assertEqual(None, existing_sources.any())

        # Now, run the copy job.
        source = getUtility(IPlainPackageCopyJobSource)
        requester = self.factory.makePerson()
        job = source.create(
            package_name="copyme",
            package_version="2.8-1",
            source_archive=source_archive,
            target_archive=target_archive,
            target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            include_binaries=False,
            requester=requester)

        # The job should be suspended and there's a PackageUpload with
        # its package_copy_job set.
        self.assertRaises(SuspendJobException, self.runJob, job)
        pu = Store.of(target_archive).find(
            PackageUpload,
            PackageUpload.package_copy_job_id == job.id).one()
        pcj = removeSecurityProxy(job).context
        self.assertEqual(pcj, pu.package_copy_job)

        # The job metadata should contain default overrides from the
        # UnknownOverridePolicy policy.
        self.assertEqual('universe', pcj.metadata['component_override'])

    def createCopyJob(self, sourcename, component, section, version):
        # Helper method to create a package copy job for a package with
        # the given sourcename, component, section and version.
        publisher = SoyuzTestPublisher()
        publisher.prepareBreezyAutotest()
        distroseries = publisher.breezy_autotest

        target_archive = self.factory.makeArchive(
            distroseries.distribution, purpose=ArchivePurpose.PRIMARY)
        source_archive = self.factory.makeArchive()

        # Publish a package in the source archive with some overridable
        # properties set to known values.
        publisher.getPubSource(
            distroseries=distroseries, sourcename=sourcename,
            component=component, section=section,
            version=version, status=PackagePublishingStatus.PUBLISHED,
            archive=source_archive)

        # Now, run the copy job.
        source = getUtility(IPlainPackageCopyJobSource)
        requester = self.factory.makePerson()
        job = source.create(
            package_name=sourcename,
            package_version=version,
            source_archive=source_archive,
            target_archive=target_archive,
            target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            include_binaries=False,
            requester=requester)

        # Run the job so it gains a PackageUpload.
        self.assertRaises(SuspendJobException, self.runJob, job)
        pcj = removeSecurityProxy(job).context
        return pcj

    def test_copying_to_main_archive_debian_override_contrib(self):
        # The job uses the overrides to map debian components to
        # the right components.
        # 'contrib' gets mapped to 'multiverse'.

        # Create debian component.
        self.factory.makeComponent('contrib')
        # Create a copy job for a package in 'contrib'.
        pcj = self.createCopyJob('package', 'contrib', 'web', '2.8.1')

        self.assertEqual('multiverse', pcj.metadata['component_override'])

    def test_copying_to_main_archive_debian_override_nonfree(self):
        # The job uses the overrides to map debian components to
        # the right components.
        # 'nonfree' gets mapped to 'multiverse'.

        # Create debian component.
        self.factory.makeComponent('non-free')
        # Create a copy job for a package in 'non-free'.
        pcj = self.createCopyJob('package', 'non-free', 'web', '2.8.1')

        self.assertEqual('multiverse', pcj.metadata['component_override'])

    def test_copying_to_main_archive_unapproved(self):
        # Uploading to a series that is in a state that precludes auto
        # approval will cause the job to suspend and a packageupload
        # created in the UNAPPROVED state.
        publisher = SoyuzTestPublisher()
        publisher.prepareBreezyAutotest()
        distroseries = publisher.breezy_autotest
        # The series is frozen so it won't auto-approve new packages.
        distroseries.status = SeriesStatus.FROZEN

        target_archive = self.factory.makeArchive(
            distroseries.distribution, purpose=ArchivePurpose.PRIMARY)
        source_archive = self.factory.makeArchive()

        # Publish a package in the source archive.
        publisher.getPubSource(
            distroseries=distroseries, sourcename="copyme",
            version="2.8-1", status=PackagePublishingStatus.PUBLISHED,
            component='multiverse', section='web',
            archive=source_archive)

        # Now put the same named package in the target archive so it has
        # ancestry.
        publisher.getPubSource(
            distroseries=distroseries, sourcename="copyme",
            version="2.8-0", status=PackagePublishingStatus.PUBLISHED,
            component='main', section='games',
            archive=target_archive)

        # Now, run the copy job.
        source = getUtility(IPlainPackageCopyJobSource)
        requester = self.factory.makePerson()
        job = source.create(
            package_name="copyme",
            package_version="2.8-1",
            source_archive=source_archive,
            target_archive=target_archive,
            target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            include_binaries=False,
            requester=requester)

        # The job should be suspended and there's a PackageUpload with
        # its package_copy_job set in the UNAPPROVED queue.
        self.assertRaises(SuspendJobException, self.runJob, job)

        pu = Store.of(target_archive).find(
            PackageUpload,
            PackageUpload.package_copy_job_id == job.id).one()
        pcj = removeSecurityProxy(job).context
        self.assertEqual(pcj, pu.package_copy_job)
        self.assertEqual(PackageUploadStatus.UNAPPROVED, pu.status)

        # The job's metadata should contain the override ancestry from
        # the target archive.
        self.assertEqual('main', pcj.metadata['component_override'])

    def test_copying_after_job_released(self):
        # The first pass of the job may have created a PackageUpload and
        # suspended the job.  Here we test the second run to make sure
        # that it actually copies the package.
        publisher = SoyuzTestPublisher()
        publisher.prepareBreezyAutotest()
        distroseries = publisher.breezy_autotest
        distroseries.changeslist = "changes@example.com"

        target_archive = self.factory.makeArchive(
            distroseries.distribution, purpose=ArchivePurpose.PRIMARY)
        source_archive = self.factory.makeArchive()

        # Publish a package in the source archive.
        publisher.getPubSource(
            distroseries=distroseries, sourcename="copyme",
            version="2.8-1", status=PackagePublishingStatus.PUBLISHED,
            archive=source_archive)

        source = getUtility(IPlainPackageCopyJobSource)
        requester = self.factory.makePerson(
            displayname="Nancy Requester", email="requester@example.com")
        with person_logged_in(target_archive.owner):
            target_archive.newComponentUploader(requester, "main")
        job = source.create(
            package_name="copyme",
            package_version="2.8-1",
            source_archive=source_archive,
            target_archive=target_archive,
            target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            include_binaries=False,
            requester=requester)

        # Run the job so it gains a PackageUpload.
        self.assertRaises(SuspendJobException, self.runJob, job)
        # Simulate the job runner suspending after getting a
        # SuspendJobException
        job.suspend()
        self.layer.txn.commit()
        self.layer.switchDbUser("launchpad_main")

        # Accept the upload to release the job then run it.
        pu = getUtility(IPackageUploadSet).getByPackageCopyJobIDs(
            [removeSecurityProxy(job).context.id]).one()
        pu.acceptFromQueue()
        # Clear existing emails so we can see only the ones the job
        # generates later.
        pop_notifications()
        self.runJob(job)

        # The job should have set the PU status to DONE:
        self.assertEqual(PackageUploadStatus.DONE, pu.status)

        # Make sure packages were actually copied.
        existing_sources = target_archive.getPublishedSources(name='copyme')
        self.assertIsNot(None, existing_sources.any())

        # It would be nice to test emails in a separate test but it would
        # require all of the same setup as above again so we might as well
        # do it here.
        emails = pop_notifications(sort_key=operator.itemgetter('To'))

        # We expect an uploader email and an announcement to the changeslist.
        self.assertEquals(2, len(emails))
        self.assertIn("requester@example.com", emails[0]['To'])
        self.assertIn("changes@example.com", emails[1]['To'])
        self.assertEqual(
            "Nancy Requester <requester@example.com>",
            emails[1]['From'])

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
        section = self.factory.makeSection()
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
        matcher = MatchesStructure.byEquality(
            component=metadata_component,
            section=metadata_section)
        self.assertThat(override, matcher)

    def test_addSourceOverride_accepts_None_component_as_no_change(self):
        # When given an override with None as the component,
        # addSourceOverride will update the section but not the
        # component.
        pcj = self.factory.makePlainPackageCopyJob()
        old_component = self.factory.makeComponent()
        old_section = self.factory.makeSection()
        pcj.addSourceOverride(SourceOverride(
            source_package_name=pcj.package_name,
            component=old_component, section=old_section))
        new_section = self.factory.makeSection()
        pcj.addSourceOverride(SourceOverride(
            source_package_name=pcj.package_name,
            component=None, section=new_section))
        self.assertEqual(old_component.name, pcj.component_name)
        self.assertEqual(new_section.name, pcj.section_name)

    def test_addSourceOverride_accepts_None_section_as_no_change(self):
        # When given an override with None for the section,
        # addSourceOverride will update the component but not the
        # section.
        pcj = self.factory.makePlainPackageCopyJob()
        old_component = self.factory.makeComponent()
        old_section = self.factory.makeSection()
        pcj.addSourceOverride(SourceOverride(
            source_package_name=pcj.package_name,
            component=old_component, section=old_section))
        new_component = self.factory.makeComponent()
        pcj.addSourceOverride(SourceOverride(
            source_package_name=pcj.package_name,
            component=new_component, section=None))
        self.assertEqual(new_component.name, pcj.component_name)
        self.assertEqual(old_section.name, pcj.section_name)

    def test_getSourceOverride(self):
        # Test the getSourceOverride which gets an ISourceOverride from
        # the metadata.
        name = self.factory.makeSourcePackageName()
        component = self.factory.makeComponent()
        section = self.factory.makeSection()
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

    def test_getPolicyImplementation_returns_policy(self):
        # getPolicyImplementation returns the ICopyPolicy that was
        # chosen for the job.
        dsd = self.factory.makeDistroSeriesDifference()
        for policy in PackageCopyPolicy.items:
            naked_job = removeSecurityProxy(
                self.makeJob(dsd, copy_policy=policy))
            self.assertEqual(
                policy, naked_job.getPolicyImplementation().enum_value)

    def test_rejects_PackageUpload_when_job_fails(self):
        # If a PCJ with a PU fails when running then we need to ensure the
        # PU gets rejected.
        target_archive = self.factory.makeArchive(
            purpose=ArchivePurpose.PRIMARY)
        source_archive = self.factory.makeArchive()
        source_pub = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename="copyme",
            version="1.0",
            archive=source_archive,
            status=PackagePublishingStatus.PUBLISHED)
        job_source = getUtility(IPlainPackageCopyJobSource)
        requester = self.factory.makePerson()
        job = job_source.create(
            package_name="copyme",
            package_version="1.0",
            source_archive=source_archive,
            target_archive=target_archive,
            target_distroseries=source_pub.distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            include_binaries=False,
            requester=requester)

        # Run the job so it gains a PackageUpload.
        self.assertRaises(SuspendJobException, self.runJob, job)
        # Simulate the job runner suspending after getting a
        # SuspendJobException
        job.suspend()
        self.layer.txn.commit()
        self.layer.switchDbUser("launchpad_main")

        # Patch the job's attemptCopy() method so it just raises an
        # exception.
        def blow_up():
            raise Exception("I blew up")
        naked_job = removeSecurityProxy(job)
        self.patch(naked_job, "attemptCopy", blow_up)

        # Accept the upload to release the job then run it.
        pu = getUtility(IPackageUploadSet).getByPackageCopyJobIDs(
            [removeSecurityProxy(job).context.id]).one()
        pu.acceptFromQueue()
        self.runJob(job)

        # The job should have set the PU status to REJECTED.
        self.assertEqual(PackageUploadStatus.REJECTED, pu.status)


class TestPlainPackageCopyJobPermissions(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_extendMetadata_edit_privilege_by_queue_admin(self):
        # A person who has any queue admin rights can edit the copy job.
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        pcj = self.factory.makePlainPackageCopyJob(target_archive=archive)
        queue_admin = self.factory.makePerson()
        with person_logged_in(pcj.target_archive.owner):
            pcj.target_archive.newQueueAdmin(queue_admin, "main")
        with person_logged_in(queue_admin):
            # This won't blow up.
            pcj.extendMetadata({})

    def test_extendMetadata_edit_privilege_by_other(self):
        # Random people cannot edit the copy job.
        pcj = self.factory.makePlainPackageCopyJob()
        self.assertRaises(
            Unauthorized, getattr, pcj, "extendMetadata")

    def test_PPA_edit_privilege_by_owner(self):
        # A PCJ for a PPA allows the PPA owner to edit it.
        ppa = self.factory.makeArchive(purpose=ArchivePurpose.PPA)
        pcj = self.factory.makePlainPackageCopyJob(target_archive=ppa)
        with person_logged_in(ppa.owner):
            # This will not throw an exception.
            pcj.extendMetadata({})

    def test_PPA_edit_privilege_by_other(self):
        # A PCJ for a PPA does not allow non-owners to edit it.
        ppa = self.factory.makeArchive(purpose=ArchivePurpose.PPA)
        pcj = self.factory.makePlainPackageCopyJob(target_archive=ppa)
        person = self.factory.makePerson()
        with person_logged_in(person):
            self.assertRaises(
                Unauthorized, getattr, pcj, "extendMetadata")


class TestPlainPackageCopyJobDbPrivileges(TestCaseWithFactory,
                                          LocalTestHelper):
    """Test that `PlainPackageCopyJob` has the database privileges it needs.

    This test looks for errors, not failures.  It's here only to see that
    these operations don't run into any privilege limitations.
    """

    layer = LaunchpadZopelessLayer

    def test_findMatchingDSDs(self):
        job = self.makeJob()
        transaction.commit()
        self.layer.switchDbUser(self.dbuser)
        removeSecurityProxy(job).findMatchingDSDs()

    def test_reportFailure(self):
        job = self.makeJob()
        transaction.commit()
        self.layer.switchDbUser(self.dbuser)
        removeSecurityProxy(job).reportFailure(CannotCopy("Mommy it hurts"))


class TestPackageCopyJobSource(TestCaseWithFactory):
    """Test the `IPackageCopyJob` utility."""

    layer = ZopelessDatabaseLayer

    def test_implements_interface(self):
        job_source = getUtility(IPackageCopyJobSource)
        self.assertThat(job_source, Provides(IPackageCopyJobSource))

    def test_wrap_accepts_None(self):
        job_source = getUtility(IPackageCopyJobSource)
        self.assertIs(None, job_source.wrap(None))

    def test_wrap_wraps_PlainPackageCopyJob(self):
        original_ppcj = self.factory.makePlainPackageCopyJob()
        IStore(PackageCopyJob).flush()
        pcj = IStore(PackageCopyJob).get(PackageCopyJob, original_ppcj.id)
        self.assertNotEqual(None, pcj)
        job_source = getUtility(IPackageCopyJobSource)
        self.assertEqual(original_ppcj, job_source.wrap(pcj))
