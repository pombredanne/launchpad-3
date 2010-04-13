# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=F0401

"""Tests for SourcePackageRecipes."""

from __future__ import with_statement

__metaclass__ = type

import unittest

from canonical.testing import DatabaseFunctionalLayer
from canonical.launchpad.webapp.authorization import check_permission
from lp.testing import (login_person, person_logged_in, TestCaseWithFactory)


class TestSourcePackageRecipe(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_sourcepackagerecipe_description(self):
        """Ensure that the SourcePackageRecipe has a proper description."""
        description = u'The whoozits and whatzits.'
        source_package_recipe = self.factory.makeSourcePackageRecipe(
            description=description)
        self.assertEqual(description, source_package_recipe.description)

    def test_distroseries(self):
        """Test that the distroseries behaves as a set."""
        recipe = self.factory.makeSourcePackageRecipe()
        distroseries = self.factory.makeDistroSeries()
        (old_distroseries,) = recipe.distroseries
        recipe.distroseries.add(distroseries)
        self.assertEqual(
            set([distroseries, old_distroseries]), set(recipe.distroseries))
        recipe.distroseries.remove(distroseries)
        self.assertEqual([old_distroseries], list(recipe.distroseries))
        recipe.distroseries.clear()
        self.assertEqual([], list(recipe.distroseries))

    def test_build_daily(self):
        """Test that build_daily behaves as a bool."""
        recipe = self.factory.makeSourcePackageRecipe()
        self.assertFalse(recipe.build_daily)
        login_person(recipe.owner)
        recipe.build_daily = True
        self.assertTrue(recipe.build_daily)

    def test_view_public(self):
        """Anyone can view a recipe with public branches."""
        owner = self.factory.makePerson()
        branch = self.factory.makeAnyBranch(owner=owner)
        with person_logged_in(owner):
            recipe = self.factory.makeSourcePackageRecipe(branches=[branch])
            self.assertTrue(check_permission('launchpad.View', recipe))
        with person_logged_in(self.factory.makePerson()):
            self.assertTrue(check_permission('launchpad.View', recipe))
        self.assertTrue(check_permission('launchpad.View', recipe))

    def test_view_private(self):
        """Recipes with private branches are restricted."""
        owner = self.factory.makePerson()
        branch = self.factory.makeAnyBranch(owner=owner, private=True)
        with person_logged_in(owner):
            recipe = self.factory.makeSourcePackageRecipe(branches=[branch])
            self.assertTrue(check_permission('launchpad.View', recipe))
        with person_logged_in(self.factory.makePerson()):
            self.assertFalse(check_permission('launchpad.View', recipe))
        self.assertFalse(check_permission('launchpad.View', recipe))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
