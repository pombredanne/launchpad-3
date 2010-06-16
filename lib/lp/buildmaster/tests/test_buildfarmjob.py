# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `IBuildFarmJob`."""

__metaclass__ = type

from datetime import datetime, timedelta
import pytz
import unittest

from storm.store import Store
from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing.layers import (
    DatabaseFunctionalLayer, LaunchpadFunctionalLayer)

from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.buildmaster.interfaces.buildfarmjob import (
    BuildFarmJobType, IBuildFarmJob, IBuildFarmJobSet, IBuildFarmJobSource,
    InconsistentBuildFarmJobError)
from lp.buildmaster.model.buildfarmjob import BuildFarmJob
from lp.testing import login, TestCaseWithFactory


class TestBuildFarmJobBase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Create a build farm job with which to test."""
        super(TestBuildFarmJobBase, self).setUp()
        self.build_farm_job = self.makeBuildFarmJob()

    def makeBuildFarmJob(self, builder=None,
                         job_type=BuildFarmJobType.PACKAGEBUILD,
                         status=BuildStatus.FULLYBUILT):
        build_farm_job = getUtility(IBuildFarmJobSource).new(
            job_type=job_type, status=status)
        removeSecurityProxy(build_farm_job).builder = builder
        return build_farm_job


class TestBuildFarmJob(TestBuildFarmJobBase):
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
        # A build farm job defaults to the NEEDSBUILD status.
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
        ten_years_ago = datetime.now(pytz.UTC) - timedelta(365*10)
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


class TestBuildFarmJobSecurity(TestBuildFarmJobBase):

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


class TestBuildFarmJobSet(TestBuildFarmJobBase):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestBuildFarmJobSet, self).setUp()
        self.builder = self.factory.makeBuilder()
        self.build_farm_jobs = []
        self.build_farm_jobs.append(
            self.makeBuildFarmJob(builder=self.builder))
        self.build_farm_jobs.append(self.makeBuildFarmJob(
            builder=self.builder,
            job_type=BuildFarmJobType.RECIPEBRANCHBUILD))
        self.build_farm_jobs.append(self.makeBuildFarmJob(
            builder=self.builder, status=BuildStatus.BUILDING))

        # For good measure, create a different type of build that will
        # also have an associated PackageBuild.
        owning_team = self.factory.makeTeam()
        archive = self.factory.makeArchive(owner=owning_team)
        self.binary_package_build = self.factory.makeBinaryPackageBuild(
            archive=archive, builder=self.builder)
        self.build_farm_jobs.append(self.binary_package_build.build_farm_job)

        self.build_farm_job_set = getUtility(IBuildFarmJobSet)

    def test_getBuildsForBuilder_all(self):
        # The default call without arguments returns all builds for the
        # builder, and not those for other builders.
        self.makeBuildFarmJob(builder=self.factory.makeBuilder())
        self.assertContentEqual(
            self.build_farm_jobs, self.build_farm_job_set.getBuildsForBuilder(
                self.builder))

    def test_getBuildsForBuilder_by_status(self):
        # If the status arg is used, the results will be filtered by
        # status.
        self.assertContentEqual(
            self.build_farm_jobs[:2],
            self.build_farm_job_set.getBuildsForBuilder(
                self.builder, status=BuildStatus.FULLYBUILT))

    def makeBuildPrivate(self, build):
        """Helper to privatise a package build."""
        removeSecurityProxy(build.archive).buildd_secret = "blah"
        removeSecurityProxy(build.archive).private = True

    def test_getBuildsForBuilder_hides_private_from_anon(self):
        # If no user is passed, all private builds are filtered out.

        # When private it is not included for anon requests.
        self.makeBuildPrivate(self.binary_package_build)
        result = self.build_farm_job_set.getBuildsForBuilder(self.builder)
        self.assertTrue(
            self.binary_package_build.build_farm_job not in result)

    def test_getBuildsForBuilder_hides_private_other_users(self):
        # Private builds are not returned for users without permission
        # to view them.
        self.makeBuildPrivate(self.binary_package_build)
        result = self.build_farm_job_set.getBuildsForBuilder(
            self.builder, user=self.factory.makePerson())
        self.assertTrue(
            self.binary_package_build.build_farm_job not in result)

    def test_getBuildsForBuilder_shows_private_to_admin(self):
        # Admin users can see private builds.
        admin_team = getUtility(ILaunchpadCelebrities).admin
        self.makeBuildPrivate(self.binary_package_build)
        result = self.build_farm_job_set.getBuildsForBuilder(
            self.builder, user=admin_team.teamowner)
        self.assertTrue(self.binary_package_build.build_farm_job in result)

    def test_getBuildsForBuilder_shows_private_to_authorised(self):
        # Similarly, if the user is in the owning team they can see it.
        self.makeBuildPrivate(self.binary_package_build)
        result = self.build_farm_job_set.getBuildsForBuilder(
            self.builder,
            user=self.binary_package_build.archive.owner.teamowner)
        self.assertTrue(self.binary_package_build.build_farm_job in result)

    def test_getBuildsForBuilder_ordered_by_date_finished(self):
        # Results are returned with the oldest build last.
        naked_build_0 = removeSecurityProxy(self.build_farm_jobs[0])
        naked_build_1 = removeSecurityProxy(self.build_farm_jobs[1])

        naked_build_0.date_finished = datetime(2008, 10, 10, tzinfo=pytz.UTC)
        naked_build_1.date_finished = datetime(2008, 11, 10, tzinfo=pytz.UTC)
        result = self.build_farm_job_set.getBuildsForBuilder(self.builder)
        self.assertEqual(self.build_farm_jobs[0], result[3])

        naked_build_0.date_finished = datetime(2008, 12, 10, tzinfo=pytz.UTC)
        result = self.build_farm_job_set.getBuildsForBuilder(self.builder)
        self.assertEqual(self.build_farm_jobs[1], result[3])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
