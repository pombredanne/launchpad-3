# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for SourcePackageRecipes."""

__metaclass__ = type

from lp.testing import (
    run_with_login, TestCase, TestCaseWithFactory, time_counter)
from canonical.testing import DatabaseFunctionalLayer, LaunchpadZopelessLayer


class TestSourcePackageRecipe(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_sourcepackagerecipe_description(self):
        """Ensure that the SourcePackageRecipe has a proper description."""
        source_package_recipe = self.factory.makeSourcePackageRecipe()
        self.assertNotEqual(None, source_package_recipe.description)
