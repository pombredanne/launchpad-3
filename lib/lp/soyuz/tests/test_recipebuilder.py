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

    def test_adapts_ISourcePackageRecipeBuildJob(self):
        # IBuildFarmJobBehavior adapts a ISourcePackageRecipeBuildJob
        job = self.factory.makeSourcePackageRecipeBuild().makeJob()
        job = IBuildFarmJobBehavior(job)
        self.assertProvides(job, IBuildFarmJobBehavior)

    def makeJob(self):
        """Create a sample `ISourcePackageRecipeBuildJob`."""
        spn = self.factory.makeSourcePackageName("apackage")
        distro = self.factory.makeDistribution(name="distro")
        distroseries = self.factory.makeDistroSeries(name="mydistro", 
            distribution=distro)
        processorfamily = ProcessorFamilySet().getByName('x86')
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, architecturetag='i386',
            processorfamily=processorfamily)
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

    def test_display_name(self):
        # display_name contains a sane description of the job
        job = self.makeJob()
        self.assertEquals(job.display_name,
            "distro/mydistro/apackage, recept")

    def test_logStartBuild(self):
        # logStartBuild will properly report the package that's being built
        job = self.makeJob()
        logger = BufferLogger()
        job.logStartBuild(logger)
        self.assertEquals(logger.buffer.getvalue(),
            "INFO: startBuild(distro/mydistro/apackage, recept)\n")

    def test_verifyBuildRequest_valid(self):
        # VerifyBuildRequest won't raise any exceptions when called with a
        # valid builder set.
        job = self.makeJob()
        builder = MockBuilder("bob-de-bouwer", SaneBuildingSlave())
        job.setBuilder(builder)
        logger = BufferLogger()
        job.verifyBuildRequest(logger)
        self.assertEquals("", logger.buffer.getvalue())

    def test__extraBuildArgs(self):
        # _extraBuildArgs will return a sane set of additional arguments
        job = self.makeJob()
        self.assertEquals({
           'author_email': u'requester@ubuntu.com',
           'suite': u'mydistro',
           'author_name': u'Joe User',
           'package_name': u'apackage',
           'archive_purpose': 'PPA',
           'ogrecomponent': 'universe',
           'recipe_text': '# bzr-builder format 0.2 deb-version 1.0\n'
                          'lp://dev/~joe/someapp/pkg\n',
            }, job._extraBuildArgs())

    def test_dispatchBuildToSlave(self):
        # Ensure dispatchBuildToSlave will make the right calls to the slave
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
        # dispatchBuildToSlave will fail when there is not chroot tarball 
        # available for the distroseries to build for.
        job = self.makeJob()
        builder = MockBuilder("bob-de-bouwer", SaneBuildingSlave())
        processorfamily = ProcessorFamilySet().getByProcessorName('386')
        builder.processor = processorfamily.processors[0]
        job.setBuilder(builder)
        logger = BufferLogger()
        self.assertRaises(CannotBuild, job.dispatchBuildToSlave, 
            "someid", logger)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
