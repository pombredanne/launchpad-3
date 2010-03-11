# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).


__metaclass__ = type


import unittest

from canonical.testing import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory


class TestSourcePackage(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_distroseries(self):
        """Test that the distroseries behaves as a set."""
        recipe = self.factory.makeSourcePackageRecipe()
        distroseries = self.factory.makeDistroSeries()
        recipe.distroseries.add(distroseries)
        self.assertEqual([distroseries], list(recipe.distroseries))
        recipe.distroseries.remove(distroseries)
        self.assertEqual([], list(recipe.distroseries))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
