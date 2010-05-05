# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for source package builds."""

from __future__ import with_statement

__metaclass__ = type

import datetime
import unittest

from pytz import utc
import transaction
from storm.locals import Store
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import LaunchpadFunctionalLayer

from canonical.launchpad.interfaces.launchpad import NotFoundError
from canonical.launchpad.webapp.authorization import check_permission
from lp.buildmaster.interfaces.buildbase import IBuildBase
from lp.buildmaster.interfaces.buildqueue import IBuildQueue
from lp.code.interfaces.sourcepackagerecipebuild import (
    ISourcePackageRecipeBuildJob, ISourcePackageRecipeBuild,
    ISourcePackageRecipeBuildSource)
from lp.testing import ANONYMOUS, login, person_logged_in, TestCaseWithFactory


class TestSourcePackageRecipeBuild(TestCaseWithFactory):
    """Test the source package build object."""

    layer = LaunchpadFunctionalLayer

    def makeSourcePackageRecipeBuild(self):
        """Create a `SourcePackageRecipeBuild` for testing."""
        return getUtility(ISourcePackageRecipeBuildSource).new(
            sourcepackage=self.factory.makeSourcePackage(),
            recipe=self.factory.makeSourcePackageRecipe(),
            archive=self.factory.makeArchive(),
            requester=self.factory.makePerson())

    def test_providesInterfaces(self):
        # SourcePackageRecipeBuild provides IBuildBase and
        # ISourcePackageRecipeBuild.
        spb = self.makeSourcePackageRecipeBuild()
        self.assertProvides(spb, IBuildBase)
        self.assertProvides(spb, ISourcePackageRecipeBuild)

    def test_saves_record(self):
        # A source package recipe build can be stored in the database
        spb = self.makeSourcePackageRecipeBuild()
        transaction.commit()
        self.assertProvides(spb, ISourcePackageRecipeBuild)

    def test_makeJob(self):
        # A build farm job can be obtained from a SourcePackageRecipeBuild
        spb = self.makeSourcePackageRecipeBuild()
        job = spb.makeJob()
        self.assertProvides(job, ISourcePackageRecipeBuildJob)

    def test_queueBuild(self):
        spb = self.makeSourcePackageRecipeBuild()
        bq = spb.queueBuild()
        self.assertProvides(bq, IBuildQueue)
        self.assertProvides(bq.specific_job, ISourcePackageRecipeBuildJob)
        self.assertEqual(True, bq.virtualized)
        self.assertIs(None, bq.processor)
        self.assertEqual(bq, spb.buildqueue_record)

    def test_title(self):
        # A recipe build's title currently consists of the base
        # branch's unique name.
        spb = self.makeSourcePackageRecipeBuild()
        title = "%s recipe build" % spb.recipe.base_branch.unique_name
        self.assertEqual(spb.title, title)

    def test_getTitle(self):
        # A recipe build job's title is the same as its build's title.
        spb = self.makeSourcePackageRecipeBuild()
        job = spb.makeJob()
        self.assertEqual(job.getTitle(), spb.title)

    def test_distribution(self):
        # A source package recipe build has a distribution derived from
        # its series.
        spb = self.makeSourcePackageRecipeBuild()
        self.assertEqual(spb.distroseries.distribution, spb.distribution)

    def test_is_private(self):
        # A source package recipe build is currently always public.
        spb = self.makeSourcePackageRecipeBuild()
        self.assertEqual(False, spb.is_private)

    def test_view_private_branch(self):
        """Recipebuilds with private branches are restricted."""
        owner = self.factory.makePerson()
        branch = self.factory.makeAnyBranch(owner=owner, private=True)
        with person_logged_in(owner):
            recipe = self.factory.makeSourcePackageRecipe(branches=[branch])
            build = self.factory.makeSourcePackageRecipeBuild(recipe=recipe)
            self.assertTrue(check_permission('launchpad.View', build))
        with person_logged_in(self.factory.makePerson()):
            self.assertFalse(check_permission('launchpad.View', build))
        login(ANONYMOUS)
        self.assertFalse(check_permission('launchpad.View', build))

    def test_view_private_archive(self):
        """Recipebuilds with private branches are restricted."""
        owner = self.factory.makePerson()
        archive = self.factory.makeArchive(owner=owner, private=True)
        build = self.factory.makeSourcePackageRecipeBuild(archive=archive)
        with person_logged_in(owner):
            self.assertTrue(check_permission('launchpad.View', build))
        with person_logged_in(self.factory.makePerson()):
            self.assertFalse(check_permission('launchpad.View', build))
        login(ANONYMOUS)
        self.assertFalse(check_permission('launchpad.View', build))

    def test_estimateDuration(self):
        # The duration estimate is currently hard-coded as two minutes.
        spb = self.makeSourcePackageRecipeBuild()
        self.assertEqual(
            datetime.timedelta(minutes=2), spb.estimateDuration())

    def test_datestarted(self):
        """Datestarted is taken from job if not specified in the build.

        Specifying datestarted in the build requires datebuilt and
        buildduration to be specified.
        """
        spb = self.makeSourcePackageRecipeBuild()
        self.assertIs(None, spb.datestarted)
        job = self.factory.makeSourcePackageRecipeBuildJob(
            recipe_build=spb).job
        job.start()
        self.assertEqual(job.date_started, spb.datestarted)
        now = datetime.datetime.now(utc)
        removeSecurityProxy(spb).datebuilt = now
        self.assertEqual(job.date_started, spb.datestarted)
        duration = datetime.timedelta(minutes=1)
        removeSecurityProxy(spb).buildduration = duration
        self.assertEqual(now - duration, spb.datestarted)

    def test_getFileByName(self):
        """getFileByName returns the logs when requested by name."""
        spb = self.factory.makeSourcePackageRecipeBuild()
        removeSecurityProxy(spb).buildlog = (
            self.factory.makeLibraryFileAlias(filename='buildlog.txt.gz'))
        self.assertEqual(spb.buildlog, spb.getFileByName('buildlog.txt.gz'))
        self.assertRaises(NotFoundError, spb.getFileByName, 'foo')
        removeSecurityProxy(spb).buildlog = (
            self.factory.makeLibraryFileAlias(filename='foo'))
        self.assertEqual(spb.buildlog, spb.getFileByName('foo'))
        self.assertRaises(NotFoundError, spb.getFileByName, 'buildlog.txt.gz')
        removeSecurityProxy(spb).upload_log = (
            self.factory.makeLibraryFileAlias(filename='upload.txt.gz'))
        self.assertEqual(spb.upload_log, spb.getFileByName('upload.txt.gz'))

    def test_binary_builds(self):
        """The binary_builds property should be populated automatically."""
        spb = self.factory.makeSourcePackageRecipeBuild()
        spr = self.factory.makeSourcePackageRelease(
            source_package_recipe_build=spb)
        self.assertEqual([], list(spb.binary_builds))
        binary = self.factory.makeBinaryPackageBuild(spr)
        self.factory.makeBinaryPackageBuild()
        Store.of(binary).flush()
        self.assertEqual([binary], list(spb.binary_builds))



def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
