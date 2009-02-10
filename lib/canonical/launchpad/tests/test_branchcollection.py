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
        collection = GenericBranchCollection(self.store, name="foo")
        self.assertEqual('foo', collection.name)

    def test_displayname(self):
        collection = GenericBranchCollection(
            self.store, displayname='Foo Bar')
        self.assertEqual('Foo Bar', collection.displayname)

    def test_getBranches_no_filter_no_branches(self):
        # If no filter is specified, then the collection is of all branches in
        # Launchpad. By default, there are no branches.
        collection = GenericBranchCollection(self.store)
        self.assertEqual([], list(collection.getBranches()))

    def test_getBranches_no_filter(self):
        # If no filter is specified, then the collection is of all branches in
        # Launchpad.
        collection = GenericBranchCollection(self.store)
        branch = self.factory.makeAnyBranch()
        self.assertEqual([branch], list(collection.getBranches()))

    def test_getBranches_product_filter(self):
        # If the specified filter is for the branches of a particular product,
        # then the collection contains only branches of that product.
        branch = self.factory.makeProductBranch()
        branch2 = self.factory.makeAnyBranch()
        collection = GenericBranchCollection(
            self.store, Branch.product == branch.product)
        self.assertEqual([branch], list(collection.getBranches()))

    def test_count(self):
        # The 'count' property of a collection is the number of elements in
        # the collection.
        collection = GenericBranchCollection(self.store)
        self.assertEqual(0, collection.count)
        for i in range(3):
            self.factory.makeAnyBranch()
        self.assertEqual(3, collection.count)

    def test_count_respects_filter(self):
        # If a collection is a subset of all possible branches, then the count
        # will be the size of that subset. That is, 'count' respects any
        # filters that are applied.
        branch = self.factory.makeProductBranch()
        branch2 = self.factory.makeAnyBranch()
        collection = GenericBranchCollection(
            self.store, Branch.product == branch.product)
        self.assertEqual(1, collection.count)

    def test_ownedBy(self):
        # 'ownedBy' returns a new collection restricted to branches owned by
        # the given person.
        branch = self.factory.makeAnyBranch()
        branch2 = self.factory.makeAnyBranch()
        collection = GenericBranchCollection(self.store).ownedBy(branch.owner)
        self.assertEqual([branch], list(collection.getBranches()))

    def test_in_product(self):
        # 'inProduct' returns a new collection restricted to branches in the
        # given product.
        #
        # XXX: JonathanLange 2009-02-11: Maybe this should be a more generic
        # method called 'onTarget' that takes a person (for junk), package or
        # product.
        branch = self.factory.makeProductBranch()
        branch2 = self.factory.makeProductBranch()
        branch3 = self.factory.makeAnyBranch()
        all_branches = GenericBranchCollection(self.store)
        collection = all_branches.inProduct(branch.product)
        self.assertEqual([branch], list(collection.getBranches()))

    # XXX: visible by user filter

    # XXX: registered by person filter

    # XXX: subscribed by person filter

    # XXX: lifecycle_status filter


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
