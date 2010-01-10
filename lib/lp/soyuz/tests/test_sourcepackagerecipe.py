# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the SourcePackageRecipe content type."""

__metaclass__ = type

import unittest

from bzrlib.plugins.builder.recipe import RecipeParser
from bzrlib.plugins.builder.tests.test_recipe import RecipeParserTests

from zope.component import getUtility
from zope.security.interfaces import Unauthorized

from canonical.testing.layers import DatabaseFunctionalLayer

from lp.code.enums import BranchType
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

    def makeBuilderRecipe(self, *branches):
        """Make a builder recipe that references `branches`.

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
        parser = RecipeParser(text)
        return parser.parse()

    def makeSourcePackageRecipeFromBuilderRecipe(self, builder_recipe):
        """Make a SourcePackageRecipe from `builder_recipe` and arbitrary other fields.
        """
        registrant = self.factory.makePerson()
        owner = self.factory.makeTeam(owner=registrant)
        distroseries = self.factory.makeDistroSeries()
        sourcepackagename = self.factory.makeSourcePackageName()
        name = self.factory.getUniqueString(u'recipe-name')
        return getUtility(ISourcePackageRecipeSource).new(
            registrant=registrant, owner=owner, distroseries=distroseries,
            sourcepackagename=sourcepackagename, name=name,
            builder_recipe=builder_recipe)

    def test_creation(self):
        # The metadata supplied when a SourcePackageRecipe is created is
        # present on the new object.
        registrant = self.factory.makePerson()
        owner = self.factory.makeTeam(owner=registrant)
        distroseries = self.factory.makeDistroSeries()
        sourcepackagename = self.factory.makeSourcePackageName()
        name = self.factory.getUniqueString(u'recipe-name')
        builder_recipe = self.makeBuilderRecipe()
        recipe = getUtility(ISourcePackageRecipeSource).new(
            registrant=registrant, owner=owner, distroseries=distroseries,
            sourcepackagename=sourcepackagename, name=name,
            builder_recipe=builder_recipe)
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

    def test_branch_links_created(self):
        # When a recipe is created, we can query it for links to the branch
        # it references.
        branch = self.factory.makeAnyBranch()
        builder_recipe = self.makeBuilderRecipe(branch)
        sp_recipe = self.makeSourcePackageRecipeFromBuilderRecipe(
            builder_recipe)
        self.assertEquals([branch], list(sp_recipe.getReferencedBranches()))

    def test_multiple_branch_links_created(self):
        # If a recipe links to more than one branch, getReferencedBranches()
        # returns all of them.
        branch1 = self.factory.makeAnyBranch()
        branch2 = self.factory.makeAnyBranch()
        builder_recipe = self.makeBuilderRecipe(branch1, branch2)
        sp_recipe = self.makeSourcePackageRecipeFromBuilderRecipe(
            builder_recipe)
        self.assertEquals(
            sorted([branch1, branch2]),
            sorted(sp_recipe.getReferencedBranches()))

    def test_random_user_cant_edit(self):
        # An arbitrary user can't set attributes.
        branch1 = self.factory.makeAnyBranch()
        builder_recipe1 = self.makeBuilderRecipe(branch1)
        sp_recipe = self.makeSourcePackageRecipeFromBuilderRecipe(
            builder_recipe1)
        branch2 = self.factory.makeAnyBranch()
        builder_recipe2 = self.makeBuilderRecipe(branch2)
        login_person(self.factory.makePerson())
        self.assertRaises(
            Unauthorized, setattr, sp_recipe, 'builder_recipe',
            builder_recipe2)

    def test_set_recipe_text_resets_branch_references(self):
        # When the recipe_text is replaced, getReferencedBranches returns
        # (only) the branches referenced by the new recipe.
        branch1 = self.factory.makeAnyBranch()
        builder_recipe1 = self.makeBuilderRecipe(branch1)
        recipe = self.makeSourcePackageRecipeFromBuilderRecipe(
            builder_recipe1)
        branch2 = self.factory.makeAnyBranch()
        builder_recipe2 = self.makeBuilderRecipe(branch2)
        login_person(recipe.owner.teamowner)
        recipe.builder_recipe = builder_recipe2
        self.assertEquals([branch2], list(recipe.getReferencedBranches()))


class TestRecipeBranchRoundTripping(RecipeParserTests, TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # This is terrible!  But it seems to work, and calling super()
        # doesn't.
        RecipeParserTests.setUp(self)
        TestCaseWithFactory.setUp(self)

    def get_recipe(self, recipe_text):
        for url in 'http://foo.org/', 'http://bar.org/':
            self.factory.makeAnyBranch(
                branch_type=BranchType.MIRRORED, url=url)
        builder_recipe = super(
            TestRecipeBranchRoundTripping, self).get_recipe(recipe_text)
        registrant = self.factory.makePerson()
        owner = self.factory.makeTeam(owner=registrant)
        distroseries = self.factory.makeDistroSeries()
        sourcepackagename = self.factory.makeSourcePackageName()
        name = self.factory.getUniqueString(u'recipe-name')
        recipe = getUtility(ISourcePackageRecipeSource).new(
            registrant=registrant, owner=owner, distroseries=distroseries,
            sourcepackagename=sourcepackagename, name=name,
            builder_recipe=builder_recipe)
        return recipe.builder_recipe


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

