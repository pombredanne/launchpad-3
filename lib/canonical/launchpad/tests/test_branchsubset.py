# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests from branch subset."""

__metaclass__ = type

import unittest

from canonical.launchpad.database.branchsubset import ProductBranchSubset
from canonical.launchpad.interfaces.branchsubset import IBranchSubset
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.testing.layers import DatabaseFunctionalLayer


class TestProductBranchSubset(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def makeSubset(self, product):
        return IBranchSubset(product)

    def test_provides_interface(self):
        product = self.factory.makeProduct()
        self.assertProvides(
            self.makeSubset(product), IBranchSubset)

    def test_name(self):
        # The name of a product subset is the name of the product.
        product = self.factory.makeProduct()
        self.assertEqual(product.name, self.makeSubset(product).name)

    def test_displayname(self):
        # The display name of a product subset is the display name of the
        # product.
        product = self.factory.makeProduct()
        self.assertEqual(
            product.displayname, self.makeSubset(product).displayname)


class TestAdapter(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_product(self):
        product = self.factory.makeProduct()
        subset = IBranchSubset(product)
        self.assertIsInstance(subset, ProductBranchSubset)
        self.assertEqual(product.name, subset.name)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

