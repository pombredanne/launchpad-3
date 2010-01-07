# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the SourcePackageRecipe content type."""

__metaclass__ = type

import unittest

from bzrlib.plugins.builder.recipe import RecipeParseError

from zope.component import getUtility
from zope.security.interfaces import Unauthorized

from canonical.testing.layers import DatabaseFunctionalLayer

from lp.soyuz.interfaces.sourcepackagerecipe import (
    ISourcePackageRecipe, ISourcePackageRecipeSource)
from lp.testing import login_person, TestCaseWithFactory


MINIMAL_RECIPE_TEXT = u'''\
# bzr-builder format 0.2 deb-version 1.0
%s
'''

class TestSourcePackageRecipe(TestCaseWithFactory):
    """Tests for `SourcePackageRecipe` objects."""

    layer = DatabaseFunctionalLayer

    def makeRecipeText(self, *branches):
        """Make a recipe text that references `branches`.

        If no branches are passed, return a recipe text that references an
        arbitrary branch.
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

    def test_source_implements_interface(self):
        # The SourcePackageRecipe class implements ISourcePackageRecipeSource.
        self.assertProvides(
            getUtility(ISourcePackageRecipeSource),
            ISourcePackageRecipeSource)

    def test_recipe_implements_interface(self):
        # SourcePackageRecipe objects implement ISourcePackageRecipe.
        recipe = self.makeRecipeWithText(self.makeRecipeText())
        self.assertProvides(recipe, ISourcePackageRecipe)

    def DONTtest_recipe_access(self):
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

    def test_random_user_cant_edit(self):
        # An arbitrary user can't set attributes.
        branch1 = self.factory.makeAnyBranch()
        text1 = self.makeRecipeText(branch1)
        recipe = self.makeRecipeWithText(text1)
        branch2 = self.factory.makeAnyBranch()
        text2 = self.makeRecipeText(branch2)
        login_person(self.factory.makePerson())
        self.assertRaises(Unauthorized, setattr, recipe, 'recipe_text', text2)

    def test_set_recipe_text_resets_branch_references(self):
        # When the recipe_text is replaced, getReferencedBranches returns
        # (only) the branches referenced by the new recipe.
        branch1 = self.factory.makeAnyBranch()
        text1 = self.makeRecipeText(branch1)
        recipe = self.makeRecipeWithText(text1)
        branch2 = self.factory.makeAnyBranch()
        text2 = self.makeRecipeText(branch2)
        login_person(recipe.owner.teamowner)
        recipe.recipe_text = text2
        self.assertEquals([branch2], list(recipe.getReferencedBranches()))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

