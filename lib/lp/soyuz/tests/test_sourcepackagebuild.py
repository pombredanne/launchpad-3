# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for source package builds."""

__metaclass__ = type

import unittest

import transaction
from zope.component import getUtility

from canonical.testing.layers import DatabaseFunctionalLayer

from lp.soyuz.interfaces.sourcepackagebuild import (
    IBuildSourcePackageFromRecipeJob, ISourcePackageBuild,
    ISourcePackageBuildSource)
from lp.testing import TestCaseWithFactory


class TestSourcePackageBuild(TestCaseWithFactory):
    """Test the source package build object."""

    layer = DatabaseFunctionalLayer

    def makeSourcePackageBuild(self):
        return getUtility(ISourcePackageBuildSource).new(
            sourcepackage=self.factory.makeSourcePackage(),
            recipe=self.factory.makeSourcePackageRecipe(),
            requester=self.factory.makePerson())

    def test_providesInterface(self):
        # SourcePackageBuild provides ISourcePackageBuild.
        spb = self.makeSourcePackageBuild()
        self.assertProvides(spb, ISourcePackageBuild)

    def test_saves_record(self):
        spb = self.makeSourcePackageBuild()
        transaction.commit()
        self.assertProvides(spb, ISourcePackageBuild)

    def test_makeJob(self):
        spb = self.makeSourcePackageBuild()
        job = spb.makeJob()
        self.assertProvides(job, IBuildSourcePackageFromRecipeJob)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
