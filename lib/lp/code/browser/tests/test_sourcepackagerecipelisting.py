# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for sourcepackagerecipe listings."""

__metaclass__ = type


from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import BrowserTestCase


class TestSourcePackageRecipeListing(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def test_project_branch_recipe_listing(self):
        branch = self.factory.makeProductBranch()
        recipe = self.factory.makeSourcePackageRecipe(branches=[branch])
        text = self.getMainText(recipe.base_branch, '+recipes')
        self.assertTextMatchesExpressionIgnoreWhitespace("""
            Source Package Recipes for lp:.*
            Name              Owner       Registered
            generic-string.*  Person-name""", text)

    def test_package_branch_recipe_listing(self):
        branch = self.factory.makePackageBranch()
        recipe = self.factory.makeSourcePackageRecipe(branches=[branch])
        text = self.getMainText(recipe.base_branch, '+recipes')
        self.assertTextMatchesExpressionIgnoreWhitespace("""
            Source Package Recipes for lp:.*
            Name             Owner       Registered
            generic-string.* Person-name""", text)
