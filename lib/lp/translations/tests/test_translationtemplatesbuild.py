# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""`TranslationTemplatesBuild` tests."""

__metaclass__ = type

from storm.store import Store
from zope.component import getUtility
from zope.interface.verify import verifyObject

from canonical.testing import DatabaseFunctionalLayer
from lp.buildmaster.enums import BuildFarmJobType
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJobSource
from lp.testing import TestCaseWithFactory
from lp.translations.interfaces.translationtemplatesbuild import (
    ITranslationTemplatesBuild,
    ITranslationTemplatesBuildSource,
    )
from lp.translations.model.translationtemplatesbuild import (
    TranslationTemplatesBuild,
    )
from lp.translations.interfaces.translationtemplatesbuildjob import (
    ITranslationTemplatesBuildJobSource,
    )


class TestTranslationTemplatesBuild(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def _findBuildForBranch(self, branch):
        """Find the `TranslationTemplatesBuild` for `branch`, if any."""
        return Store.of(branch).find(
            TranslationTemplatesBuild,
            TranslationTemplatesBuild.branch == branch).one()

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
        self.assertEqual(build_farm_job, build.build_farm_job)
        self.assertEqual(branch, build.branch)

    def test_created_by_buildjobsource(self):
        # ITranslationTemplatesBuildJobSource.create also creates a
        # TranslationTemplatesBuild.  This utility will become obsolete
        # later.
        jobset = getUtility(ITranslationTemplatesBuildJobSource)
        branch = self.factory.makeBranch()

        translationtemplatesbuildjob = jobset.create(branch)
        self.assertNotEqual(None, self._findBuildForBranch(branch))
