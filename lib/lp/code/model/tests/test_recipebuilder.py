# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test RecipeBuildBehavior."""

# pylint: disable-msg=F0401

__metaclass__ = type

import re
import transaction
import unittest

from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.testing import LaunchpadFunctionalLayer
from canonical.launchpad.scripts.logger import BufferLogger

from lp.buildmaster.interfaces.builder import CannotBuild
from lp.buildmaster.interfaces.buildfarmjob import BuildFarmJobType
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior)
from lp.buildmaster.manager import RecordingSlave
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.code.model.recipebuilder import RecipeBuildBehavior
from lp.code.model.sourcepackagerecipebuild import (
    SourcePackageRecipeBuild)
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.adapters.archivedependencies import (
    get_sources_list_for_building)
from lp.soyuz.model.processor import ProcessorFamilySet
from lp.soyuz.tests.soyuzbuilddhelpers import (
    MockBuilder, OkSlave)
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
        processorfamily = ProcessorFamilySet().getByProcessorName('386')
        distroseries.newArch(
            'i386', processorfamily, True, self.factory.makePerson())
        sourcepackage = self.factory.makeSourcePackage(spn, distroseries)
        requester = self.factory.makePerson(email="requester@ubuntu.com",
            name="joe", displayname="Joe User")
        somebranch = self.factory.makeBranch(owner=requester, name="pkg",
            product=self.factory.makeProduct("someapp"))
        recipe = self.factory.makeSourcePackageRecipe(requester, requester,
             distroseries, u"recept", u"Recipe description",
             branches=[somebranch])
        spb = self.factory.makeSourcePackageRecipeBuild(
            sourcepackage=sourcepackage, recipe=recipe, requester=requester,
            distroseries=distroseries)
        job = spb.makeJob()
        job_id = removeSecurityProxy(job.job).id
        BuildQueue(job_type=BuildFarmJobType.RECIPEBRANCHBUILD, job=job_id)
        job = IBuildFarmJobBehavior(job)
        return job

    def test_display_name(self):
        # display_name contains a sane description of the job
        job = self.makeJob()
        self.assertEquals(job.display_name,
            "Mydistro, recept, joe")

    def test_logStartBuild(self):
        # logStartBuild will properly report the package that's being built
        job = self.makeJob()
        logger = BufferLogger()
        job.logStartBuild(logger)
        self.assertEquals(logger.buffer.getvalue(),
            "INFO: startBuild(Mydistro, recept, joe)\n")

    def test_verifyBuildRequest_valid(self):
        # VerifyBuildRequest won't raise any exceptions when called with a
        # valid builder set.
        job = self.makeJob()
        builder = MockBuilder("bob-de-bouwer", OkSlave())
        job.setBuilder(builder)
        logger = BufferLogger()
        job.verifyBuildRequest(logger)
        self.assertEquals("", logger.buffer.getvalue())

    def test_verifyBuildRequest_non_virtual(self):
        # verifyBuildRequest will raise if a non-virtual builder is proposed.
        job = self.makeJob()
        builder = MockBuilder('non-virtual builder', OkSlave())
        builder.virtualized = False
        job.setBuilder(builder)
        logger = BufferLogger()
        e = self.assertRaises(AssertionError, job.verifyBuildRequest, logger)
        self.assertEqual(
            'Attempt to build virtual item on a non-virtual builder.', str(e))

    def test_verifyBuildRequest_bad_pocket(self):
        # verifyBuildRequest will raise if a bad pocket is proposed.
        build = self.factory.makeSourcePackageRecipeBuild(
            pocket=PackagePublishingPocket.SECURITY)
        job = self.factory.makeSourcePackageRecipeBuildJob(recipe_build=build)
        job = IBuildFarmJobBehavior(job.specific_job)
        job.setBuilder(MockBuilder("bob-de-bouwer", OkSlave()))
        e = self.assertRaises(
            AssertionError, job.verifyBuildRequest, BufferLogger())
        self.assertIn('invalid pocket due to the series status of', str(e))

    def test__extraBuildArgs(self):
        # _extraBuildArgs will return a sane set of additional arguments
        bzr_builder_config = """
            [builddmaster]
            bzr_builder_sources_list = deb http://foo %(series)s main
            """
        config.push("bzr_builder_config", bzr_builder_config)
        self.addCleanup(config.pop, "bzr_builder_config")

        job = self.makeJob()
        distroarchseries = job.build.distroseries.architectures[0]
        expected_archives = get_sources_list_for_building(
            job.build, distroarchseries, None)
        expected_archives.append(
            "deb http://foo %s main" % job.build.distroseries.name)
        self.assertEqual({
           'author_email': u'requester@ubuntu.com',
           'suite': u'mydistro',
           'author_name': u'Joe User',
           'archive_purpose': 'PPA',
           'ogrecomponent': 'universe',
           'recipe_text': '# bzr-builder format 0.2 deb-version 0+{revno}\n'
                          'lp://dev/~joe/someapp/pkg\n',
           'archives': expected_archives,
           'distroseries_name': job.build.distroseries.name,
            }, job._extraBuildArgs(distroarchseries))

    def test_extraBuildArgs_withBadConfigForBzrBuilderPPA(self):
        # Ensure _extraBuildArgs doesn't blow up with a badly formatted
        # bzr_builder_sources_list in the config.
        bzr_builder_config = """
            [builddmaster]
            bzr_builder_sources_list = deb http://foo %(series) main
            """
        # (note the missing 's' in %(series)

        config.push("bzr_builder_config", bzr_builder_config)
        self.addCleanup(config.pop, "bzr_builder_config")

        job = self.makeJob()
        distroarchseries = job.build.distroseries.architectures[0]
        expected_archives = get_sources_list_for_building(
            job.build, distroarchseries, None)
        logger = BufferLogger()
        self.assertEqual({
           'author_email': u'requester@ubuntu.com',
           'suite': u'mydistro',
           'author_name': u'Joe User',
           'archive_purpose': 'PPA',
           'ogrecomponent': 'universe',
           'recipe_text': '# bzr-builder format 0.2 deb-version 0+{revno}\n'
                          'lp://dev/~joe/someapp/pkg\n',
           'archives': expected_archives,
           'distroseries_name': job.build.distroseries.name,
            }, job._extraBuildArgs(distroarchseries, logger))
        self.assertIn(
            "Exception processing bzr_builder_sources_list:",
            logger.buffer.getvalue())

    def test_extraBuildArgs_withNoBZrBuilderConfigSet(self):
        # Ensure _extraBuildArgs doesn't blow up when
        # bzr_builder_sources_list isn't set.
        job = self.makeJob()
        distroarchseries = job.build.distroseries.architectures[0]
        args = job._extraBuildArgs(distroarchseries)
        expected_archives = get_sources_list_for_building(
            job.build, distroarchseries, None)
        self.assertEqual(args["archives"], expected_archives)


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
        self.assertEquals(
            build_args[0], job.buildfarmjob.generateSlaveBuildCookie())
        self.assertEquals(build_args[1], "sourcepackagerecipe")
        self.assertEquals(build_args[3], {})
        distroarchseries = job.build.distroseries.architectures[0]
        self.assertEqual(build_args[4], job._extraBuildArgs(distroarchseries))

    def test_dispatchBuildToSlave_nochroot(self):
        # dispatchBuildToSlave will fail when there is not chroot tarball
        # available for the distroseries to build for.
        job = self.makeJob()
        builder = MockBuilder("bob-de-bouwer", OkSlave())
        processorfamily = ProcessorFamilySet().getByProcessorName('386')
        builder.processor = processorfamily.processors[0]
        job.setBuilder(builder)
        logger = BufferLogger()
        self.assertRaises(CannotBuild, job.dispatchBuildToSlave,
            "someid", logger)

    def test_getById(self):
        job = self.makeJob()
        transaction.commit()
        self.assertEquals(
            job.build, SourcePackageRecipeBuild.getById(job.build.id))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
