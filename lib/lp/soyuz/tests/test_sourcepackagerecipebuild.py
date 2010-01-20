# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for source package builds."""

__metaclass__ = type

import datetime
import unittest

import transaction
from zope.component import getUtility

from canonical.testing.layers import DatabaseFunctionalLayer

from lp.soyuz.interfaces.buildqueue import IBuildQueue
from lp.soyuz.interfaces.sourcepackagerecipebuild import (
    ISourcePackageRecipeBuildJob, ISourcePackageRecipeBuild,
    ISourcePackageRecipeBuildSource)
from lp.testing import TestCaseWithFactory


class TestSourcePackageRecipeBuild(TestCaseWithFactory):
    """Test the source package build object."""

    layer = DatabaseFunctionalLayer

    def makeSourcePackageRecipeBuild(self):
        """Create a `SourcePackageRecipeBuild` for testing."""
        return getUtility(ISourcePackageRecipeBuildSource).new(
            sourcepackage=self.factory.makeSourcePackage(),
            recipe=self.factory.makeSourcePackageRecipe(),
            archive=self.factory.makeArchive(),
            requester=self.factory.makePerson())

    def test_providesInterface(self):
        # SourcePackageRecipeBuild provides ISourcePackageRecipeBuild.
        spb = self.makeSourcePackageRecipeBuild()
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

    def test_createBuildQueueEntry(self):
        spb = self.makeSourcePackageRecipeBuild()
        bq = spb.createBuildQueueEntry()
        self.assertProvides(bq, IBuildQueue)
        self.assertProvides(bq.specific_job, ISourcePackageRecipeBuildJob)
        self.assertEqual(True, bq.virtualized)
        self.assertIs(None, bq.processor)
        self.assertEqual(bq, spb.buildqueue_record)

    def test_getTitle(self):
        # A build farm job implements getTitle().
        spb = self.makeSourcePackageRecipeBuild()
        job = spb.makeJob()
        # The title describes the job and should be recognizable by users.
        # Hence the choice of the "ingredients" below.
        title = "%s-%s-%s-recipe-build-job" % (
            job.build.distroseries.displayname, job.build.sourcepackagename,
            job.build.archive.displayname)
        self.assertEqual(job.getTitle(), title)

    def test_distribution(self):
        # A source package recipe build has a distribution derived from
        # its series.
        spb = self.makeSourcePackageRecipeBuild()
        self.assertEqual(spb.distroseries.distribution, spb.distribution)

    def test_is_private(self):
        # A source package recipe build is currently always public.
        spb = self.makeSourcePackageRecipeBuild()
        self.assertEqual(False, spb.is_private)

    def test_estimateDuration(self):
        # The duration estimate is currently hard-coded as two minutes.
        spb = self.makeSourcePackageRecipeBuild()
        self.assertEqual(
            datetime.timedelta(minutes=2), spb.estimateDuration())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
