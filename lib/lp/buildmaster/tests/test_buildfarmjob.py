# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `IBuildFarmJob`."""

__metaclass__ = type

import unittest

from storm.store import Store
from zope.component import getUtility

from canonical.database.sqlbase import flush_database_updates
from canonical.testing.layers import DatabaseFunctionalLayer

from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.buildmaster.interfaces.buildfarmjob import (
    BuildFarmJobType, IBuildFarmJob, IBuildFarmJobSource)
from lp.buildmaster.model.buildfarmjob import BuildFarmJob
from lp.testing import TestCaseWithFactory


class TestBuildFarmJob(TestCaseWithFactory):
    """Tests for the build farm job object."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Create a build farm job with which to test."""
        super(TestBuildFarmJob, self).setUp()
        self.build_farm_job = self.makeBuildFarmJob()

    def makeBuildFarmJob(self):
        return getUtility(IBuildFarmJobSource).new(
            job_type=BuildFarmJobType.PACKAGEBUILD)

    def test_has_concrete_build_farm_job(self):
        # This temporary property returns true if the instance
        # corresponds to a concrete database record, even if
        # db updates have not yet been flushed, and false
        # otherwise.
        concrete_build_farm_job = self.makeBuildFarmJob()
        self.failUnless(concrete_build_farm_job.has_concrete_build_farm_job)

        mem_build_farm_job = BuildFarmJob(
            job_type=BuildFarmJobType.PACKAGEBUILD)
        self.failIf(mem_build_farm_job.has_concrete_build_farm_job)

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

    def test_unimplemented_methods(self):
        # A build farm job leaves the implementation of various
        # methods for derived classes.
        self.assertRaises(NotImplementedError, self.build_farm_job.score)
        self.assertRaises(NotImplementedError, self.build_farm_job.getName)
        self.assertRaises(NotImplementedError, self.build_farm_job.getTitle)

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

    def test_log_url(self):
        self.failUnless(False)

    def test_buildqueue_record(self):
        self.failUnless(False)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
