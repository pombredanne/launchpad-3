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

    def makeRecipeText(self, *branches):
        """Make a recipe that references `branches`.

        XXX.
        """
        if len(branches) == 0:
            branches = (self.factory.makeAnyBranch(),)
        base_branch = branches[0]
        other_branches = branches[1:]
        text = MINIMAL_RECIPE_TEXT % base_branch.bzr_identity
        for i, branch in enumerate(other_branches):
            text += 'merge dummy-%s %s\n' % (i, branch.bzr_identity)
        return text

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

    def test_recipe_access(self):
        # For now, the exact text passed when a recipe is created is available
        # as the 'recipe_text' attribute on the recipe object.
        text = self.makeRecipeText()
        recipe = self.makeRecipeWithText(text)
        self.assertEquals(text, recipe.recipe_text)

    def test_invalid_recipe_text(self):
        # Attempting to create a recipe with an invalid recipe text fails.
        self.assertRaises(RecipeParseError, self.makeRecipeWithText, u'')

    def test_branch_links_created(self):
        # When a recipe is created, we can query it for links to the branch
        # it references.
        branch = self.factory.makeAnyBranch()
        text = self.makeRecipeText(branch)
        recipe = self.makeRecipeWithText(text)
        self.assertEquals([branch], list(recipe.getReferencedBranches()))

    def test_multiple_branch_links_created(self):
        # If a recipe links to more than one branch, getReferencedBranches()
        # returns all of them.
        branch1 = self.factory.makeAnyBranch()
        branch2 = self.factory.makeAnyBranch()
        text = self.makeRecipeText(branch1, branch2)
        recipe = self.makeRecipeWithText(text)
        self.assertEquals(
            sorted([branch1, branch2]),
            sorted(recipe.getReferencedBranches()))



def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

