import pdb
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type

import unittest

from canonical.testing import LaunchpadFunctionalLayer
from canonical.launchpad.scripts.logger import BufferLogger

from lp.buildmaster.interfaces.builder import CannotBuild
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior)
from lp.buildmaster.manager import RecordingSlave
from lp.soyuz.model.sourcepackagerecipebuild import (
    SourcePackageRecipeBuild)
from lp.soyuz.model.recipebuilder import RecipeBuildBehavior
from lp.soyuz.model.processor import ProcessorFamilySet
from lp.soyuz.tests.soyuzbuilddhelpers import (MockBuilder,
    SaneBuildingSlave,)
from lp.soyuz.tests.test_publishing import (
    SoyuzTestPublisher,)
from lp.testing import TestCaseWithFactory


class TestRecipeBuilder(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

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
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, architecturetag='i386')
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
        test_publisher = SoyuzTestPublisher()
        test_publisher.addFakeChroots(job.build.distroseries)
        slave = RecordingSlave("i386-slave-1", "http://myurl", "vmhost")
        builder = MockBuilder("bob-de-bouwer", slave)
        processorfamily = ProcessorFamilySet().getByProcessorName('386')
        builder.processor = processorfamily.processors[0]
        job.setBuilder(builder)
        logger = BufferLogger()
        job.dispatchBuildToSlave("someid", logger)
        logger.buffer.seek(0)
        self.assertEquals(
            "DEBUG: Initiating build 1-someid on http://fake:0000\n",
            logger.buffer.readline())
        self.assertEquals(["ensurepresent", "build"],
                          [call[0] for call in slave.calls])
        build_args = slave.calls[1][1]
        self.assertEquals(build_args[0], "1-someid")
        self.assertEquals(build_args[1], "sourcepackagerecipe")
        self.assertEquals(build_args[3], {})
        self.assertEquals(build_args[4], job._extraBuildArgs())

    def test_dispatchBuildToSlave_nochroot(self):
        job = self.makeJob()
        builder = MockBuilder("bob-de-bouwer", SaneBuildingSlave())
        processorfamily = ProcessorFamilySet().getByProcessorName('386')
        builder.processor = processorfamily.processors[0]
        job.setBuilder(builder)
        logger = BufferLogger()
        self.assertRaises(CannotBuild, job.dispatchBuildToSlave, 
            "someid", logger)

    def test_getById(self):
        job = self.makeJob()
        build_id = job.build.id
        self.assertEquals(
            job.build, SourcePackageRecipeBuild.getById(build_id))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
