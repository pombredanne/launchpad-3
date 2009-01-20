# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests from branch subset."""

__metaclass__ = type

import unittest

from canonical.launchpad.database.branchsubset import (
    PersonBranchSubset, ProductBranchSubset)
from canonical.launchpad.interfaces.branchsubset import IBranchSubset
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.testing.layers import DatabaseFunctionalLayer


class BranchSubsetTestsMixin:

    layer = DatabaseFunctionalLayer

    def makeComponent(self):
        raise NotImplementedError(self.makeComponent)

    def makeSubset(self, component):
        raise NotImplementedError(self.makeSubset)

    def makeBranchInSubset(self, component):
        raise NotImplementedError(self.makeBranchInSubset)

    def test_provides_interface(self):
        component = self.makeComponent()
        self.assertProvides(
            self.makeSubset(component), IBranchSubset)

    def test_name(self):
        # The name of a component subset is the name of the component.
        component = self.makeComponent()
        self.assertEqual(component.name, self.makeSubset(component).name)

    def test_displayname(self):
        # The display name of a component subset is the display name of the
        # component.
        component = self.makeComponent()
        self.assertEqual(
            component.displayname, self.makeSubset(component).displayname)

    def test_getBranches_empty(self):
        component = self.makeComponent()
        subset = self.makeSubset(component)
        self.assertEqual([], list(subset.getBranches()))

    def test_getBranches_non_empty(self):
        component = self.makeComponent()
        branch = self.makeBranchInSubset(component)
        subset = self.makeSubset(component)
        self.assertEqual([branch], list(subset.getBranches()))

    def test_count_empty(self):
        component = self.makeComponent()
        subset = self.makeSubset(component)
        self.assertEqual(0, subset.count)

    def test_count_non_empty(self):
        component = self.makeComponent()
        branch = self.makeBranchInSubset(component)
        subset = self.makeSubset(component)
        self.assertEqual(1, subset.count)


class TestProductBranchSubset(TestCaseWithFactory, BranchSubsetTestsMixin):

    layer = DatabaseFunctionalLayer

    def makeComponent(self):
        return self.factory.makeProduct()

    def makeSubset(self, component):
        return IBranchSubset(component)

    def makeBranchInSubset(self, component):
        return self.factory.makeProductBranch(product=component)


class TestPersonBranchSubset(TestCaseWithFactory, BranchSubsetTestsMixin):

    layer = DatabaseFunctionalLayer

    def makeComponent(self):
        return self.factory.makePerson()

    def makeSubset(self, person):
        return IBranchSubset(person)

    def makeBranchInSubset(self, component):
        return self.factory.makePersonalBranch(owner=component)


class TestAdapter(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_product(self):
        product = self.factory.makeProduct()
        subset = IBranchSubset(product)
        self.assertIsInstance(subset, ProductBranchSubset)
        self.assertEqual(product.name, subset.name)

    def test_person(self):
        # The default IBranchSubset for a person is all of the branches owned
        # by that person.
        # XXX: Is this a good idea? - jml
        person = self.factory.makePerson()
        subset = IBranchSubset(person)
        self.assertIsInstance(subset, PersonBranchSubset)
        self.assertEqual(person.name, subset.name)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

