# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type

import unittest

from bzrlib.plugins.builder.recipe import RecipeParseError

from zope.component import getUtility

from canonical.testing.layers import DatabaseFunctionalLayer


from lp.soyuz.interfaces.sourcepackagerecipe import ISourcePackageRecipeSource
from lp.testing import TestCaseWithFactory

MINIMAL_RECIPE_TEXT = u'''\
# bzr-builder format 0.2 deb-version 1.0
%s
'''

class TestSourcePackageRecipeCreation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_creation(self):
        # The metadata supplied when a SourcePackageRecipe is created is
        # present on the new object.
        registrant = self.factory.makePerson()
        owner = self.factory.makeTeam(owner=registrant)
        distroseries = self.factory.makeDistroSeries()
        sourcepackagename = self.factory.makeSourcePackageName()
        name = self.factory.getUniqueString(u'recipe-name')
        recipe_text = self.makeRecipeText()
        recipe = getUtility(ISourcePackageRecipeSource).new(
            registrant=registrant, owner=owner, distroseries=distroseries,
            sourcepackagename=sourcepackagename, name=name,
            recipe=recipe_text)
        self.assertEquals(
            (registrant, owner, distroseries, sourcepackagename, name),
            (recipe.registrant, recipe.owner, recipe.distroseries,
             recipe.sourcepackagename, recipe.name))

    def makeRecipeText(self, branch=None):
        if branch is None:
            branch = self.factory.makeAnyBranch()
        return MINIMAL_RECIPE_TEXT % branch.bzr_identity

    def makeRecipeWithText(self, text):
        """Make a SourcePackageRecipe with `text` and arbitrary other fields.
        """
        registrant = self.factory.makePerson()
        owner = self.factory.makeTeam(owner=registrant)
        distroseries = self.factory.makeDistroSeries()
        sourcepackagename = self.factory.makeSourcePackageName()
        name = self.factory.getUniqueString(u'recipe-name')
        return getUtility(ISourcePackageRecipeSource).new(
            registrant=registrant, owner=owner, distroseries=distroseries,
            sourcepackagename=sourcepackagename, name=name, recipe=text)

    def test_invalid_recipe_text(self):
        # Attempting to create a recipe with an invalid recipe text fails.
        self.assertRaises(RecipeParseError, self.makeRecipeWithText, u'')

    def test_branch_links_created(self):
        #
        branch = self.factory.makeAnyBranch()
        text = self.makeRecipeText(branch)
        recipe = self.makeRecipeWithText(text)
        self.assertEquals([branch], list(recipe.getReferencedBranches()))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

