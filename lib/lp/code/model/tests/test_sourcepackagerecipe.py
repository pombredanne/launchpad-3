# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).


__metaclass__ = type


import unittest

from canonical.testing import DatabaseFunctionalLayer
from lp.testing import login_person, TestCaseWithFactory


class TestSourcePackageRecipe(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

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

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
