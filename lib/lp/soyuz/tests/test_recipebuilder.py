# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type

import unittest

from canonical.testing import DatabaseFunctionalLayer
from canonical.launchpad.scripts.logger import BufferLogger

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

    def test_adapts_IBuildSourcePackageFromRecipeJob(self):
        job = self.factory.makeSourcePackageBuild().makeJob()
        job = IBuildFarmJobBehavior(job)
        self.assertProvides(job, IBuildFarmJobBehavior)

    def makeJob(self):
        spn = self.factory.makeSourcePackageName("apackage")
        distro = self.factory.makeDistribution(name="distro")
        distroseries = self.factory.makeDistroSeries(name="mydistro", distribution=distro)
        sourcepackage = self.factory.makeSourcePackage(spn, distroseries)
        recipe = self.factory.makeSourcePackageRecipe(name=u"recept")
        requester = self.factory.makePerson()
        spb = self.factory.makeSourcePackageBuild(sourcepackage=sourcepackage,
            recipe=recipe, requester=requester)
        job = spb.makeJob()
        job = IBuildFarmJobBehavior(job)
        return job

    def test_displayName(self):
        job = self.makeJob()
        self.assertEquals(job.displayName,
            "distro/mydistro/apackage, recept")

    def test_logStartBuild(self):
        job = self.makeJob()
        logger = BufferLogger()
        job.logStartBuild(logger)
        self.assertEquals(logger.buffer.getvalue(),
            "INFO: startBuild(distro/mydistro/apackage, recept)\n")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
