# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""`TranslationTemplatesBuild` tests."""

__metaclass__ = type

from storm.store import Store
import transaction
from zope.component import getUtility
from zope.interface.verify import verifyObject

from canonical.config import config
from canonical.testing import LaunchpadZopelessLayer
from lp.buildmaster.enums import BuildFarmJobType
from lp.buildmaster.interfaces.buildfarmjob import (
    IBuildFarmJob,
    IBuildFarmJobSource,
    )
from lp.testing import TestCaseWithFactory
from lp.translations.interfaces.translationtemplatesbuild import (
    ITranslationTemplatesBuild,
    ITranslationTemplatesBuildSource,
    )
from lp.translations.interfaces.translationtemplatesbuildjob import (
    ITranslationTemplatesBuildJobSource,
    )
from lp.translations.model.translationtemplatesbuild import (
    TranslationTemplatesBuild,
    )


class TestTranslationTemplatesBuild(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def _makeBuildFarmJob(self):
        """Create a `BuildFarmJob` for testing."""
        source = getUtility(IBuildFarmJobSource)
        return source.new(BuildFarmJobType.TRANSLATIONTEMPLATESBUILD)

    def test_baseline(self):
        source = getUtility(ITranslationTemplatesBuildSource)
        branch = self.factory.makeBranch()
        build_farm_job = self._makeBuildFarmJob()

        build = source.create(build_farm_job, branch)

        self.assertTrue(verifyObject(ITranslationTemplatesBuild, build))
        self.assertTrue(verifyObject(IBuildFarmJob, build))
        self.assertEqual(build_farm_job, build.build_farm_job)
        self.assertEqual(branch, build.branch)

    def test_permissions(self):
        # The branch scanner creates TranslationTemplatesBuilds.  It has
        # the database privileges it needs for that.
        branch = self.factory.makeBranch()
        transaction.commit()
        self.layer.switchDbUser(config.branchscanner.dbuser)
        utility = getUtility(ITranslationTemplatesBuildSource)
        build_farm_job = self._makeBuildFarmJob()
        utility.create(build_farm_job, branch)

        # Writing the new objects to the database violates no access
        # restrictions.
        Store.of(build_farm_job).flush()

    def test_created_by_buildjobsource(self):
        # ITranslationTemplatesBuildJobSource.create also creates a
        # TranslationTemplatesBuild.  This utility will become obsolete
        # later.
        jobset = getUtility(ITranslationTemplatesBuildJobSource)
        source = getUtility(ITranslationTemplatesBuildSource)
        branch = self.factory.makeBranch()

        jobset.create(branch)

        builds = list(source.findByBranch(branch))
        self.assertEqual(1, len(builds))
        self.assertIsInstance(builds[0], TranslationTemplatesBuild)

    def test_getSpecificJob(self):
        source = getUtility(ITranslationTemplatesBuildSource)
        build_farm_job = self._makeBuildFarmJob()
        branch = self.factory.makeBranch()
        build = source.create(build_farm_job, branch)

        self.assertEqual(build, build_farm_job.getSpecificJob())

    def test_findByBranch(self):
        source = getUtility(ITranslationTemplatesBuildSource)
        build_farm_job = self._makeBuildFarmJob()
        branch = self.factory.makeBranch()

        self.assertContentEqual([], source.findByBranch(branch))

        build = source.create(build_farm_job, branch)

        by_branch = list(source.findByBranch(branch))
        self.assertEqual([build], by_branch)

    def test_get(self):
        source = getUtility(ITranslationTemplatesBuildSource)
        build_farm_job = self._makeBuildFarmJob()
        branch = self.factory.makeBranch()
        build = source.create(build_farm_job, branch)

        self.assertEqual(build, source.getByID(build.id))

    def test_get_returns_none_if_not_found(self):
        source = getUtility(ITranslationTemplatesBuildSource)
        build_farm_job = self._makeBuildFarmJob()
        branch = self.factory.makeBranch()
        build = source.create(build_farm_job, branch)

        self.assertIs(None, source.getByID(build.id + 999))

    def test_getByBuildFarmJob(self):
        source = getUtility(ITranslationTemplatesBuildSource)
        build_farm_job = self._makeBuildFarmJob()
        branch = self.factory.makeBranch()
        build = source.create(build_farm_job, branch)

        self.assertEqual(build, source.getByBuildFarmJob(build_farm_job))

    def test_getByBuildFarmJobs(self):
        source = getUtility(ITranslationTemplatesBuildSource)
        build_farm_jobs = []
        builds = []
        for i in xrange(10):
            build_farm_job = self._makeBuildFarmJob()
            branch = self.factory.makeBranch()
            build = source.create(build_farm_job, branch)
            build_farm_jobs.append(build_farm_job)
            builds.append(build)

        self.assertContentEqual(
            builds,
            source.getByBuildFarmJobs(build_farm_jobs))

    def test_getByBuildFarmJob_returns_none_if_not_found(self):
        source = getUtility(ITranslationTemplatesBuildSource)
        build_farm_job = self._makeBuildFarmJob()
        branch = self.factory.makeBranch()
        source.create(build_farm_job, branch)

        another_job = self._makeBuildFarmJob()
        self.assertIs(
            None,
            source.getByBuildFarmJob(another_job))
