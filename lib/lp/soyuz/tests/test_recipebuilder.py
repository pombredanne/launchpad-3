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
from lp.soyuz.model.processor import ProcessorFamilySet
from lp.soyuz.tests.soyuzbuilddhelpers import (MockBuilder,
    SaneBuildingSlave)
from lp.testing import TestCaseWithFactory

class TestRecipeBuilder(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_providesInterface(self):
        # RecipeBuildBehavior provides IBuildFarmJobBehavior.
        recipe_builder = RecipeBuildBehavior(None)
        self.assertProvides(recipe_builder, IBuildFarmJobBehavior)

    def test_adapts_IBuildSourcePackageFromRecipeJob(self):
        job = self.factory.makeSourcePackageRecipeBuild().makeJob()
        job = IBuildFarmJobBehavior(job)
        self.assertProvides(job, IBuildFarmJobBehavior)

    def makeJob(self):
        spn = self.factory.makeSourcePackageName("apackage")
        distro = self.factory.makeDistribution(name="distro")
        distroseries = self.factory.makeDistroSeries(name="mydistro", 
            distribution=distro)
        sourcepackage = self.factory.makeSourcePackage(spn, distroseries)
        requester = self.factory.makePerson(email="requester@ubuntu.com",
            name="joe", displayname="Joe User")
        somebranch = self.factory.makeBranch(owner=requester, name="pkg", 
            product=self.factory.makeProduct("someapp"))
        recipe = self.factory.makeSourcePackageRecipe(requester, requester, 
             distroseries, spn, u"recept", somebranch)
        spb = self.factory.makeSourcePackageRecipeBuild(sourcepackage=sourcepackage,
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

    def test_verifyBuildRequest_valid(self):
        job = self.makeJob()
        builder = MockBuilder("bob-de-bouwer", SaneBuildingSlave())
        job.setBuilder(builder)
        logger = BufferLogger()
        job.verifyBuildRequest(logger)
        self.assertEquals("", logger.buffer.getvalue())

    # XXX: Make sure that a verifyBuildRequest() for a recipe upload to an
    # archive that the user doesn't have access to fails.

    def test__extraBuildArgs(self):
        job = self.makeJob()
        self.assertEquals({
           'author_email': u'requester@ubuntu.com',
           'suite': u'mydistro',
           'author_name': u'Joe User',
           'package_name': u'apackage',
           'archive_purpose': 'PPA',
           'recipe_text': '# bzr-builder format 0.2 deb-version 1.0\n'
                          'lp://dev/~joe/someapp/pkg\n',
            }, job._extraBuildArgs())

    def test_dispatchBuildToSlave(self):
        job = self.makeJob()
        # XXX: Use RecordingSlave
        builder = MockBuilder("bob-de-bouwer", SaneBuildingSlave())
        processorfamily = ProcessorFamilySet().getByProcessorName('386')
        builder.processor = processorfamily.processors[0]
        job.setBuilder(builder)
        logger = BufferLogger()
        job.dispatchBuildToSlave("someid", logger)
        logger.buffer.seek(0)
        self.assertEquals(
            "DEBUG: Initiating build foo-someid on %s\n" % builder.url,
            logger.buffer.readline())
        self.assertEquals(
            """INFO: bob-de-bouwer (http://):
            """, logger.buffer.getvalue())
        # XXX: Check rest of logger output


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
