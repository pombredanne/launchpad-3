# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type

import unittest

from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior)
from lp.code.adapters.recipebuilder import RecipeBuildBehavior
from lp.testing import TestCase


class TestRecipeBuilder(TestCase):

    def test_providesInterface(self):
        # RecipeBuildBehavior provides IBuildFarmJobBehavior.
        recipe_builder = RecipeBuildBehavior(None)
        self.assertProvides(recipe_builder, IBuildFarmJobBehavior)

    def test_adapts_IBuildSourcePackageFromRecipeJob(self):
        # XXX: We don't actually have a IBuildSourcePackageFromRecipeJob yet,
        # so this test doesn't do anything.
        pass


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
