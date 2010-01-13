# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for source package builds."""

__metaclass__ = type

import unittest

import transaction
from zope.component import getUtility

from canonical.testing.layers import DatabaseFunctionalLayer

from lp.soyuz.interfaces.sourcepackagerecipebuild import (
    ISourcePackageRecipeBuild, ISourcePackageRecipeBuildSource)
from lp.testing import TestCaseWithFactory


class TestSourcePackageRecipeBuild(TestCaseWithFactory):
    """Test the source package build object."""

    layer = DatabaseFunctionalLayer

    def makeSourcePackageRecipeBuild(self):
        return getUtility(ISourcePackageRecipeBuildSource).new(
            sourcepackage=self.factory.makeSourcePackage(),
            recipe=self.factory.makeSourcePackageRecipe(),
            requester=self.factory.makePerson())

    def test_providesInterface(self):
        # SourcePackageRecipeBuild provides ISourcePackageRecipeBuild.
        spb = self.makeSourcePackageRecipeBuild()
        self.assertProvides(spb, ISourcePackageRecipeBuild)

    def test_saves_record(self):
        spb = self.makeSourcePackageRecipeBuild()
        transaction.commit()
        self.assertProvides(spb, ISourcePackageRecipeBuild)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
