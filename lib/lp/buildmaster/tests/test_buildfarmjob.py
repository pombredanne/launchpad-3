# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `IBuildFarmJob`."""

__metaclass__ = type

import unittest

from storm.store import Store
from zope.component import getUtility

from canonical.database.sqlbase import flush_database_updates
from canonical.testing.layers import DatabaseFunctionalLayer

from lp.buildmaster.interfaces.buildfarmjob import (
    BuildFarmJobType, IBuildFarmJob, IBuildFarmJobSource)
from lp.buildmaster.model.buildfarmjob import BuildFarmJob
from lp.testing import TestCaseWithFactory


class TestBuildFarmJob(TestCaseWithFactory):
    """Tests for the build farm job object."""

    layer = DatabaseFunctionalLayer

    def makeBuildFarmJob(self):
        return getUtility(IBuildFarmJobSource).new(
            job_type=BuildFarmJobType.PACKAGEBUILD)

    def test_providesInterface(self):
        # BuildFarmJob provides IBuildFarmJob
        build_farm_job = self.makeBuildFarmJob()
        self.assertProvides(build_farm_job, IBuildFarmJob)

    def test_saves_record(self):
        # A build farm job can be stored in the database.
        build_farm_job = self.makeBuildFarmJob()
        store = Store.of(build_farm_job)
        flush_database_updates()
        retrieved_job = store.find(
            BuildFarmJob,
            BuildFarmJob.id == build_farm_job.id).one()
        self.assertEqual(build_farm_job, retrieved_job)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
