# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for branch collections."""

__metaclass__ = type

from datetime import datetime, timedelta
import unittest

import pytz
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.database.branch import Branch
from canonical.launchpad.database.branchcollection import (
    GenericBranchCollection, PersonBranchCollection, ProductBranchCollection)
from canonical.launchpad.interfaces.branchcollection import IBranchCollection
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.testing.layers import DatabaseFunctionalLayer


class TestGenericBranchCollection(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.store = getUtility(IStoreSelector).get(
            MAIN_STORE, DEFAULT_FLAVOR)

    def test_name(self):
        subset = GenericBranchCollection(self.store, name="foo")
        self.assertEqual('foo', subset.name)

    def test_displayname(self):
        subset = GenericBranchCollection(self.store, displayname='Foo Bar')
        self.assertEqual('Foo Bar', subset.displayname)

    def test_getBranches_no_filter(self):
        # If no filter is specified, then the collection is of all branches in
        # Launchpad.
        subset = GenericBranchCollection(self.store)
        all_branches = self.store.find(Branch)
        self.assertEqual(list(all_branches), list(subset.getBranches()))

    def test_getBranches_product_filter(self):
        # If the specified filter is for the branches of a particular product,
        # then the collection contains only branches of that product.
        branch = self.factory.makeProductBranch()
        subset = GenericBranchCollection(
            self.store, Branch.product == branch.product)
        all_branches = self.store.find(Branch)
        self.assertEqual([branch], list(subset.getBranches()))

    def test_count(self):
        # The 'count' property of a collection is the number of elements in
        # the collection.
        subset = GenericBranchCollection(self.store)
        num_all_branches = self.store.find(Branch).count()
        self.assertEqual(num_all_branches, subset.count)


class TestAdapter(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_product(self):
        product = self.factory.makeProduct()
        subset = IBranchCollection(product)
        self.assertIsInstance(subset, ProductBranchCollection)
        self.assertEqual(product.name, subset.name)

    def test_person(self):
        # The default IBranchCollection for a person is all of the branches
        # owned by that person.
        person = self.factory.makePerson()
        subset = IBranchCollection(person)
        self.assertIsInstance(subset, PersonBranchCollection)
        self.assertEqual(person.name, subset.name)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

