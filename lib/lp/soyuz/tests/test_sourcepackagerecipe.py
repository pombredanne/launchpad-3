# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.testing.layers import DatabaseFunctionalLayer

from lp.soyuz.interfaces.sourcepackagerecipe import ISourcePackageRecipeSource
from lp.testing import TestCaseWithFactory


class TestSourcePackageRecipeCreation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_creation(self):
        # The metadata supplied when a SourcePackageRecipe is created is
        # present on the new object.
        registrant = self.factory.makePerson()
        owner = self.factory.makeTeam(owner=registrant)
        distroseries = self.factory.makeDistroSeries()
        sourcepackagename = self.factory.makeSourcePackageName()
        name = self.factory.getUniqueString()
        recipe_text = '#'
        recipe = getUtility(ISourcePackageRecipeSource).new(
            registrant=registrant, owner=owner, distroseries=distroseries,
            sourcepackagename=sourcepackagename, name=name,
            recipe=recipe_text)
        self.assertEquals(
            (registrant, owner, distroseries, sourcepackagename, name),
            (recipe.registrant, recipe.owner, recipe.distroseries,
             recipe.sourcepackagename, recipe.name))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

