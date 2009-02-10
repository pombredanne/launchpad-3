# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for branch collections."""

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.database.branch import Branch
from canonical.launchpad.database.branchcollection import (
    GenericBranchCollection)
from canonical.launchpad.interfaces.branchcollection import IBranchCollection
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.testing.databasehelpers import (
    remove_all_sample_data_branches)
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.testing.layers import DatabaseFunctionalLayer


class TestGenericBranchCollection(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        remove_all_sample_data_branches()
        self.store = getUtility(IStoreSelector).get(
            MAIN_STORE, DEFAULT_FLAVOR)

    def test_provides_branchcollection(self):
        self.assertProvides(
            GenericBranchCollection(self.store), IBranchCollection)

    def test_name(self):
        subset = GenericBranchCollection(self.store, name="foo")
        self.assertEqual('foo', subset.name)

    def test_displayname(self):
        subset = GenericBranchCollection(self.store, displayname='Foo Bar')
        self.assertEqual('Foo Bar', subset.displayname)

    def test_getBranches_no_filter_no_branches(self):
        # If no filter is specified, then the collection is of all branches in
        # Launchpad. By default, there are no branches.
        subset = GenericBranchCollection(self.store)
        self.assertEqual([], list(subset.getBranches()))

    def test_getBranches_no_filter(self):
        # If no filter is specified, then the collection is of all branches in
        # Launchpad.
        subset = GenericBranchCollection(self.store)
        branch = self.factory.makeAnyBranch()
        self.assertEqual([branch], list(subset.getBranches()))

    def test_getBranches_product_filter(self):
        # If the specified filter is for the branches of a particular product,
        # then the collection contains only branches of that product.
        branch = self.factory.makeProductBranch()
        branch2 = self.factory.makeAnyBranch()
        subset = GenericBranchCollection(
            self.store, Branch.product == branch.product)
        all_branches = self.store.find(Branch)
        self.assertEqual([branch], list(subset.getBranches()))

    def test_count(self):
        # The 'count' property of a collection is the number of elements in
        # the collection.
        subset = GenericBranchCollection(self.store)
        self.assertEqual(0, subset.count)
        for i in range(3):
            self.factory.makeAnyBranch()
        self.assertEqual(3, subset.count)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

