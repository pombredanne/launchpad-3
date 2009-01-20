# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests from branch subset."""

__metaclass__ = type

import unittest

from canonical.launchpad.database.branchsubset import (
    PersonBranchSubset, ProductBranchSubset)
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

    def test_getBranches_empty(self):
        product = self.factory.makeProduct()
        subset = self.makeSubset(product)
        self.assertEqual([], list(subset.getBranches()))

    def test_getBranches_non_empty(self):
        product = self.factory.makeProduct()
        branch = self.factory.makeProductBranch(product=product)
        subset = self.makeSubset(product)
        self.assertEqual([branch], list(subset.getBranches()))


class TestPersonBranchSubset(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def makeSubset(self, person):
        return IBranchSubset(person)

    def test_provides_interface(self):
        person = self.factory.makePerson()
        self.assertProvides(
            self.makeSubset(person), IBranchSubset)

    def test_name(self):
        # The name of a person subset is the name of the person.
        person = self.factory.makePerson()
        self.assertEqual(person.name, self.makeSubset(person).name)

    def test_displayname(self):
        # The display name of a person subset is the display name of the
        # person.
        person = self.factory.makePerson()
        self.assertEqual(
            person.displayname, self.makeSubset(person).displayname)

    def test_getBranches_empty(self):
        person = self.factory.makePerson()
        subset = self.makeSubset(person)
        self.assertEqual([], list(subset.getBranches()))

    def test_getBranches_non_empty(self):
        person = self.factory.makePerson()
        branch = self.factory.makePersonalBranch(owner=person)
        subset = self.makeSubset(person)
        self.assertEqual([branch], list(subset.getBranches()))


class TestAdapter(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_product(self):
        product = self.factory.makeProduct()
        subset = IBranchSubset(product)
        self.assertIsInstance(subset, ProductBranchSubset)
        self.assertEqual(product.name, subset.name)

    def test_person(self):
        person = self.factory.makePerson()
        subset = IBranchSubset(person)
        self.assertIsInstance(subset, PersonBranchSubset)
        self.assertEqual(person.name, subset.name)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

