# Copyright 2010-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for classes that implement IHasRecipes."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from lp.code.interfaces.hasrecipes import IHasRecipes
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class TestIHasRecipes(TestCaseWithFactory):
    """Test that the correct objects implement the interface."""

    layer = DatabaseFunctionalLayer

    def test_branch_implements_hasrecipes(self):
        # Branches should implement IHasRecipes.
        branch = self.factory.makeBranch()
        self.assertProvides(branch, IHasRecipes)

    def test_branch_recipes(self):
        # IBranch.recipes should provide all the SourcePackageRecipes attached
        # to that branch.
        base_branch = self.factory.makeBranch()
        self.factory.makeSourcePackageRecipe(branches=[base_branch])
        self.factory.makeSourcePackageRecipe(branches=[base_branch])
        self.factory.makeSourcePackageRecipe()
        self.assertEqual(2, base_branch.recipes.count())

    def test_branch_recipes_nonbase(self):
        # IBranch.recipes should provide all the SourcePackageRecipes
        # that refer to the branch, even as a non-base branch.
        base_branch = self.factory.makeBranch()
        nonbase_branch = self.factory.makeBranch()
        recipe = self.factory.makeSourcePackageRecipe(
            branches=[base_branch, nonbase_branch])
        self.factory.makeSourcePackageRecipe()
        self.assertEqual(recipe, nonbase_branch.recipes.one())

    def test_git_repository_implements_hasrecipes(self):
        # Git repositories should implement IHasRecipes.
        repository = self.factory.makeGitRepository()
        self.assertProvides(repository, IHasRecipes)

    def test_git_repository_recipes(self):
        # IGitRepository.recipes should provide all the SourcePackageRecipes
        # attached to that repository.
        base_ref1, base_ref2 = self.factory.makeGitRefs(
            paths=["refs/heads/ref1", "refs/heads/ref2"])
        [other_ref] = self.factory.makeGitRefs()
        self.factory.makeSourcePackageRecipe(branches=[base_ref1])
        self.factory.makeSourcePackageRecipe(branches=[base_ref2])
        self.factory.makeSourcePackageRecipe(branches=[other_ref])
        self.assertEqual(2, base_ref1.repository.recipes.count())

    def test_git_repository_recipes_nonbase(self):
        # IGitRepository.recipes should provide all the SourcePackageRecipes
        # that refer to the repository, even as a non-base branch.
        [base_ref] = self.factory.makeGitRefs()
        [nonbase_ref] = self.factory.makeGitRefs()
        [other_ref] = self.factory.makeGitRefs()
        recipe = self.factory.makeSourcePackageRecipe(
            branches=[base_ref, nonbase_ref])
        self.factory.makeSourcePackageRecipe(branches=[other_ref])
        self.assertEqual(recipe, nonbase_ref.repository.recipes.one())

    def test_person_implements_hasrecipes(self):
        # Person should implement IHasRecipes.
        person = self.factory.makePerson()
        self.assertProvides(person, IHasRecipes)

    def test_person_recipes(self):
        # IPerson.recipes should provide all the SourcePackageRecipes
        # owned by that person.
        person = self.factory.makePerson()
        self.factory.makeSourcePackageRecipe(owner=person)
        self.factory.makeSourcePackageRecipe(owner=person)
        self.factory.makeSourcePackageRecipe()
        self.assertEqual(2, person.recipes.count())

    def test_product_implements_hasrecipes(self):
        # Product should implement IHasRecipes.
        product = self.factory.makeProduct()
        self.assertProvides(product, IHasRecipes)

    def test_product_recipes(self):
        # IProduct.recipes should provide all the SourcePackageRecipes
        # attached to that product's branches and Git repositories.
        product = self.factory.makeProduct()
        branch = self.factory.makeBranch(product=product)
        [ref] = self.factory.makeGitRefs(target=product)
        recipe1 = self.factory.makeSourcePackageRecipe(branches=[branch])
        recipe2 = self.factory.makeSourcePackageRecipe(branches=[branch])
        self.factory.makeSourcePackageRecipe()
        recipe3 = self.factory.makeSourcePackageRecipe(branches=[ref])
        recipe4 = self.factory.makeSourcePackageRecipe(branches=[ref])
        self.factory.makeSourcePackageRecipe(
            branches=self.factory.makeGitRefs())
        self.assertContentEqual(
            [recipe1, recipe2, recipe3, recipe4], product.recipes)
