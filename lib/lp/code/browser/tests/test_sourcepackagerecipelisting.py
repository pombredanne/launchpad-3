# Copyright 2010-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for sourcepackagerecipe listings."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from lp.testing import (
    BrowserTestCase,
    person_logged_in,
    record_two_runs,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import HasQueryCount


class TestSourcePackageRecipeListing(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def test_project_branch_recipe_listing(self):
        # We can see recipes for the project.
        branch = self.factory.makeProductBranch()
        recipe = self.factory.makeSourcePackageRecipe(branches=[branch])
        text = self.getMainText(recipe.base_branch, '+recipes')
        self.assertTextMatchesExpressionIgnoreWhitespace("""
            Source Package Recipes for lp:.*
            Name              Owner       Registered
            spr-name.*        Person-name""", text)

    def test_package_branch_recipe_listing(self):
        # We can see recipes for the package.
        branch = self.factory.makePackageBranch()
        recipe = self.factory.makeSourcePackageRecipe(branches=[branch])
        text = self.getMainText(recipe.base_branch, '+recipes')
        self.assertTextMatchesExpressionIgnoreWhitespace("""
            Source Package Recipes for lp:.*
            Name             Owner       Registered
            spr-name.*       Person-name""", text)

    def test_branch_query_count(self):
        # The number of queries required to render the list of all recipes
        # for a branch is constant in the number of owners and recipes.
        person = self.factory.makePerson()
        branch = self.factory.makeProductBranch(owner=person)

        def create_recipe():
            with person_logged_in(person):
                self.factory.makeSourcePackageRecipe(branches=[branch])

        recorder1, recorder2 = record_two_runs(
            lambda: self.getMainText(branch, "+recipes"), create_recipe, 5)
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))

    def test_project_query_count(self):
        # The number of queries required to render the list of all recipes
        # for a project is constant in the number of owners, branches, and
        # recipes.
        person = self.factory.makePerson()
        project = self.factory.makeProduct(owner=person)

        def create_recipe():
            with person_logged_in(person):
                branch = self.factory.makeProductBranch(product=project)
                self.factory.makeSourcePackageRecipe(branches=[branch])

        recorder1, recorder2 = record_two_runs(
            lambda: self.getMainText(project, "+recipes"), create_recipe, 5)
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))

    def test_person_query_count(self):
        # The number of queries required to render the list of all recipes
        # for a person is constant in the number of projects, branches, and
        # recipes.
        person = self.factory.makePerson()

        def create_recipe():
            with person_logged_in(person):
                branch = self.factory.makeProductBranch(owner=person)
                self.factory.makeSourcePackageRecipe(
                    owner=person, branches=[branch])

        recorder1, recorder2 = record_two_runs(
            lambda: self.getMainText(person, "+recipes"), create_recipe, 5)
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))
