# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type

import unittest

from canonical.testing import DatabaseFunctionalLayer

from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior)
from lp.soyuz.model.recipebuilder import RecipeBuildBehavior
from lp.testing import TestCaseWithFactory


class TestRecipeBuilder(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_providesInterface(self):
        # RecipeBuildBehavior provides IBuildFarmJobBehavior.
        recipe_builder = RecipeBuildBehavior(None)
        self.assertProvides(recipe_builder, IBuildFarmJobBehavior)

    def makeJob(self):
        return getUtility(IBuildSourcePackageFromRecipeJobSource).new(
            build, job)

    def test_adapts_IBuildSourcePackageFromRecipeJob(self):
        job = self.factory.makeSourcePackageBuild().makeJob()
        job = IBuildFarmJobBehavior(job)
        self.assertProvides(job, IBuildFarmJobBehavior)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
