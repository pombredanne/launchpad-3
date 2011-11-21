# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `IBuildFarmJob`."""

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )

import pytz
from storm.store import Store
from testtools.matchers import Equals
from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from canonical.database.sqlbase import flush_database_updates
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.app.errors import NotFoundError
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.buildmaster.enums import (
    BuildFarmJobType,
    BuildStatus,
    )
from lp.buildmaster.interfaces.buildfarmjob import (
    IBuildFarmJob,
    IBuildFarmJobSet,
    IBuildFarmJobSource,
    InconsistentBuildFarmJobError,
    )
from lp.buildmaster.model.buildfarmjob import BuildFarmJob
from lp.testing import (
    login,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.matchers import HasQueryCount
from lp.translations.interfaces.translationtemplatesbuild import (
    ITranslationTemplatesBuildSource,
    )


class TestBuildFarmJobMixin:

    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Create a build farm job with which to test."""
        super(TestBuildFarmJobMixin, self).setUp()
        self.build_farm_job = self.makeBuildFarmJob()

    def makeBuildFarmJob(self, builder=None,
                         job_type=BuildFarmJobType.PACKAGEBUILD,
                         status=BuildStatus.NEEDSBUILD,
                         date_finished=None):
        """A factory method for creating PackageBuilds.

        This is not included in the launchpad test factory because
        a build farm job should never be instantiated outside the
        context of a derived class (such as a BinaryPackageBuild
        or eventually a SPRecipeBuild).
        """
        build_farm_job = getUtility(IBuildFarmJobSource).new(
            job_type=job_type, status=status)
        removeSecurityProxy(build_farm_job).builder = builder
        removeSecurityProxy(build_farm_job).date_started = date_finished
        removeSecurityProxy(build_farm_job).date_finished = date_finished
        return build_farm_job


class TestBuildFarmJob(TestBuildFarmJobMixin, TestCaseWithFactory):
    """Tests for the build farm job object."""

    def test_providesInterface(self):
        # BuildFarmJob provides IBuildFarmJob
        self.assertProvides(self.build_farm_job, IBuildFarmJob)

    def test_saves_record(self):
        # A build farm job can be stored in the database.
        flush_database_updates()
        store = Store.of(self.build_farm_job)
        retrieved_job = store.find(
            BuildFarmJob,
            BuildFarmJob.id == self.build_farm_job.id).one()
        self.assertEqual(self.build_farm_job, retrieved_job)

    def test_default_values(self):
        # We flush the database updates to ensure sql defaults
        # are set for various attributes.
        flush_database_updates()
        self.assertEqual(
            BuildStatus.NEEDSBUILD, self.build_farm_job.status)
        # The date_created is set automatically.
        self.assertTrue(self.build_farm_job.date_created is not None)
        # The job type is required to create a build farm job.
        self.assertEqual(
            BuildFarmJobType.PACKAGEBUILD, self.build_farm_job.job_type)
        # Failure count defaults to zero.
        self.assertEqual(0, self.build_farm_job.failure_count)
        # Other attributes are unset by default.
        self.assertEqual(None, self.build_farm_job.processor)
        self.assertEqual(None, self.build_farm_job.virtualized)
        self.assertEqual(None, self.build_farm_job.date_started)
        self.assertEqual(None, self.build_farm_job.date_finished)
        self.assertEqual(None, self.build_farm_job.date_first_dispatched)
        self.assertEqual(None, self.build_farm_job.builder)
        self.assertEqual(None, self.build_farm_job.log)
        self.assertEqual(None, self.build_farm_job.log_url)
        self.assertEqual(None, self.build_farm_job.buildqueue_record)

    def test_unimplemented_methods(self):
        # A build farm job leaves the implementation of various
        # methods for derived classes.
        self.assertRaises(NotImplementedError, self.build_farm_job.score)
        self.assertRaises(NotImplementedError, self.build_farm_job.getName)
        self.assertRaises(NotImplementedError, self.build_farm_job.getTitle)
        self.assertRaises(NotImplementedError, self.build_farm_job.makeJob)

    def test_jobStarted(self):
        # Starting a job sets the date_started and status, as well as
        # the date first dispatched, if it is the first dispatch of
        # this job.
        self.build_farm_job.jobStarted()
        self.assertTrue(self.build_farm_job.date_first_dispatched is not None)
        self.assertTrue(self.build_farm_job.date_started is not None)
        self.assertEqual(
            BuildStatus.BUILDING, self.build_farm_job.status)

    def test_jobReset(self):
        # Resetting a job sets its status back to NEEDSBUILD and unsets
        # the date_started.
        self.build_farm_job.jobStarted()
        self.build_farm_job.jobReset()
        self.failUnlessEqual(
            BuildStatus.NEEDSBUILD, self.build_farm_job.status)
        self.failUnless(self.build_farm_job.date_started is None)

    def test_jobAborted(self):
        # Aborting a job sets its status back to NEEDSBUILD and unsets
        # the date_started.
        self.build_farm_job.jobStarted()
        self.build_farm_job.jobAborted()
        self.failUnlessEqual(
            BuildStatus.NEEDSBUILD, self.build_farm_job.status)
        self.failUnless(self.build_farm_job.date_started is None)

    def test_jobCancel(self):
        # Cancelling a job sets its status to CANCELLED.
        self.build_farm_job.jobStarted()
        self.build_farm_job.jobCancel()
        self.assertEqual(BuildStatus.CANCELLED, self.build_farm_job.status)

    def test_title(self):
        # The default title simply uses the job type's title.
        self.assertEqual(
            self.build_farm_job.job_type.title,
            self.build_farm_job.title)

    def test_duration_none(self):
        # If either start or finished is none, the duration will be
        # none.
        self.build_farm_job.jobStarted()
        self.failUnlessEqual(None, self.build_farm_job.duration)

        self.build_farm_job.jobAborted()
        removeSecurityProxy(self.build_farm_job).date_finished = (
            datetime.now(pytz.UTC))
        self.failUnlessEqual(None, self.build_farm_job.duration)

    def test_duration_set(self):
        # If both start and finished are defined, the duration will be
        # returned.
        now = datetime.now(pytz.UTC)
        duration = timedelta(1)
        naked_bfj = removeSecurityProxy(self.build_farm_job)
        naked_bfj.date_started = now
        naked_bfj.date_finished = now + duration
        self.failUnlessEqual(duration, self.build_farm_job.duration)

    def test_date_created(self):
        # date_created can be passed optionally when creating a
        # bulid farm job to ensure we don't get identical timestamps
        # when transactions are committed.
        ten_years_ago = datetime.now(pytz.UTC) - timedelta(365 * 10)
        build_farm_job = getUtility(IBuildFarmJobSource).new(
            job_type=BuildFarmJobType.PACKAGEBUILD,
            date_created=ten_years_ago)
        self.failUnlessEqual(ten_years_ago, build_farm_job.date_created)

    def test_getSpecificJob_none(self):
        # An exception is raised if there is no related specific job.
        self.assertRaises(
            InconsistentBuildFarmJobError, self.build_farm_job.getSpecificJob)

    def test_getSpecificJob_unimplemented_type(self):
        # An `IBuildFarmJob` with an unimplemented type results in an
        # exception.
        removeSecurityProxy(self.build_farm_job).job_type = (
            BuildFarmJobType.RECIPEBRANCHBUILD)

        self.assertRaises(
            InconsistentBuildFarmJobError, self.build_farm_job.getSpecificJob)


class TestBuildFarmJobSecurity(TestBuildFarmJobMixin, TestCaseWithFactory):

    def test_view_build_farm_job(self):
        # Anonymous access can read public builds, but not edit.
        self.failUnlessEqual(
            BuildStatus.NEEDSBUILD, self.build_farm_job.status)
        self.assertRaises(
            Unauthorized, setattr, self.build_farm_job,
            'status', BuildStatus.FULLYBUILT)

    def test_edit_build_farm_job(self):
        # Users with edit access can update attributes.
        login('admin@canonical.com')
        self.build_farm_job.status = BuildStatus.FULLYBUILT
        self.failUnlessEqual(
            BuildStatus.FULLYBUILT, self.build_farm_job.status)


class TestBuildFarmJobSet(TestBuildFarmJobMixin, TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestBuildFarmJobSet, self).setUp()
        self.builder = self.factory.makeBuilder()
        self.build_farm_job_set = getUtility(IBuildFarmJobSet)

    def createTranslationTemplateBuild(self):
        build_farm_job_source = getUtility(IBuildFarmJobSource)
        build_farm_job = build_farm_job_source.new(
            BuildFarmJobType.TRANSLATIONTEMPLATESBUILD)
        source = getUtility(ITranslationTemplatesBuildSource)
        branch = self.factory.makeBranch()
        return source.create(build_farm_job, branch)

    def createSourcePackageRecipeBuild(self):
        sprb = self.factory.makeSourcePackageRecipeBuild()
        Store.of(sprb).flush()
        return sprb

    def createBinaryPackageBuild(self):
        build = self.factory.makeBinaryPackageBuild()
        return build

    def createBuilds(self):
        builds = []
        for i in xrange(2):
            builds.append(self.createBinaryPackageBuild())
            builds.append(self.createTranslationTemplateBuild())
            builds.append(self.createSourcePackageRecipeBuild())
        return builds

    def test_getSpecificJobs(self):
        builds = self.createBuilds()
        specific_jobs = self.build_farm_job_set.getSpecificJobs(
            [build.build_farm_job for build in builds])
        self.assertContentEqual(
            builds, specific_jobs)

    def test_getSpecificJobs_preserves_order(self):
        builds = self.createBuilds()
        specific_jobs = self.build_farm_job_set.getSpecificJobs(
            [build.build_farm_job for build in builds])
        self.assertEqual(
            [(build.id, build.__class__) for build in builds],
            [(job.id, job.__class__) for job in specific_jobs])

    def test_getSpecificJobs_empty(self):
        self.assertContentEqual(
            [],
            self.build_farm_job_set.getSpecificJobs([]))

    def test_getSpecificJobs_sql_queries_count(self):
        # getSpecificJobs issues a constant number of queries.
        builds = self.createBuilds()
        build_farm_jobs = [build.build_farm_job for build in builds]
        flush_database_updates()
        with StormStatementRecorder() as recorder:
            self.build_farm_job_set.getSpecificJobs(
                build_farm_jobs)
        builds2 = self.createBuilds()
        build_farm_jobs.extend([build.build_farm_job for build in builds2])
        flush_database_updates()
        with StormStatementRecorder() as recorder2:
            self.build_farm_job_set.getSpecificJobs(
                build_farm_jobs)
        self.assertThat(recorder, HasQueryCount(Equals(recorder2.count)))

    def test_getSpecificJobs_no_specific_job(self):
        build_farm_job_source = getUtility(IBuildFarmJobSource)
        build_farm_job = build_farm_job_source.new(
            BuildFarmJobType.TRANSLATIONTEMPLATESBUILD)
        flush_database_updates()
        self.assertRaises(
            InconsistentBuildFarmJobError,
            self.build_farm_job_set.getSpecificJobs, [build_farm_job])

    def test_getBuildsForBuilder_all(self):
        # The default call without arguments returns all builds for the
        # builder, and not those for other builders.
        build1 = self.makeBuildFarmJob(builder=self.builder)
        build2 = self.makeBuildFarmJob(builder=self.builder)
        self.makeBuildFarmJob(builder=self.factory.makeBuilder())

        result = self.build_farm_job_set.getBuildsForBuilder(self.builder)

        self.assertContentEqual([build1, build2], result)

    def test_getBuildsForBuilder_by_status(self):
        # If the status arg is used, the results will be filtered by
        # status.
        successful_builds = [
            self.makeBuildFarmJob(
                builder=self.builder, status=BuildStatus.FULLYBUILT),
            self.makeBuildFarmJob(
                builder=self.builder, status=BuildStatus.FULLYBUILT),
            ]
        self.makeBuildFarmJob(builder=self.builder)

        query_by_status = self.build_farm_job_set.getBuildsForBuilder(
                self.builder, status=BuildStatus.FULLYBUILT)

        self.assertContentEqual(successful_builds, query_by_status)

    def _makePrivateAndNonPrivateBuilds(self, owning_team=None):
        """Return a tuple of a private and non-private build farm job."""
        if owning_team is None:
            owning_team = self.factory.makeTeam()
        archive = self.factory.makeArchive(owner=owning_team, private=True)
        private_build = self.factory.makeBinaryPackageBuild(
            archive=archive, builder=self.builder)
        private_build = removeSecurityProxy(private_build).build_farm_job
        other_build = self.makeBuildFarmJob(builder=self.builder)
        return (private_build, other_build)

    def test_getBuildsForBuilder_hides_private_from_anon(self):
        # If no user is passed, all private builds are filtered out.
        private_build, other_build = self._makePrivateAndNonPrivateBuilds()

        result = self.build_farm_job_set.getBuildsForBuilder(self.builder)

        self.assertContentEqual([other_build], result)

    def test_getBuildsForBuilder_hides_private_other_users(self):
        # Private builds are not returned for users without permission
        # to view them.
        private_build, other_build = self._makePrivateAndNonPrivateBuilds()

        result = self.build_farm_job_set.getBuildsForBuilder(
            self.builder, user=self.factory.makePerson())

        self.assertContentEqual([other_build], result)

    def test_getBuildsForBuilder_shows_private_to_admin(self):
        # Admin users can see private builds.
        admin_team = getUtility(ILaunchpadCelebrities).admin
        private_build, other_build = self._makePrivateAndNonPrivateBuilds()

        result = self.build_farm_job_set.getBuildsForBuilder(
            self.builder, user=admin_team.teamowner)

        self.assertContentEqual([private_build, other_build], result)

    def test_getBuildsForBuilder_shows_private_to_authorised(self):
        # Similarly, if the user is in the owning team they can see it.
        owning_team = self.factory.makeTeam()
        private_build, other_build = self._makePrivateAndNonPrivateBuilds(
            owning_team=owning_team)

        result = self.build_farm_job_set.getBuildsForBuilder(
            self.builder,
            user=owning_team.teamowner)

        self.assertContentEqual([private_build, other_build], result)

    def test_getBuildsForBuilder_ordered_by_date_finished(self):
        # Results are returned with the oldest build last.
        build_1 = self.makeBuildFarmJob(
            builder=self.builder,
            date_finished=datetime(2008, 10, 10, tzinfo=pytz.UTC))
        build_2 = self.makeBuildFarmJob(
            builder=self.builder,
            date_finished=datetime(2008, 11, 10, tzinfo=pytz.UTC))

        result = self.build_farm_job_set.getBuildsForBuilder(self.builder)
        self.assertEqual([build_2, build_1], list(result))

        removeSecurityProxy(build_2).date_finished = (
            datetime(2008, 8, 10, tzinfo=pytz.UTC))
        result = self.build_farm_job_set.getBuildsForBuilder(self.builder)

        self.assertEqual([build_1, build_2], list(result))

    def test_getByID(self):
        # getByID returns a job by id.
        build_1 = self.makeBuildFarmJob(
            builder=self.builder,
            date_finished=datetime(2008, 10, 10, tzinfo=pytz.UTC))
        flush_database_updates()
        self.assertEquals(
            build_1, self.build_farm_job_set.getByID(build_1.id))

    def test_getByID_nonexistant(self):
        # getByID raises NotFoundError for unknown job ids.
        self.assertRaises(NotFoundError,
            self.build_farm_job_set.getByID, 423432432432)
