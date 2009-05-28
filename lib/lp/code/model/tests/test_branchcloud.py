# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for IBranchCloud provider."""

__metaclass__ = type

from datetime import datetime, timedelta
import unittest

import pytz
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.code.interfaces.branch import BranchType, IBranchCloud
from lp.testing import TestCaseWithFactory, time_counter
from canonical.launchpad.testing.databasehelpers import (
    remove_all_sample_data_branches)
from canonical.launchpad.webapp.interfaces import MASTER_FLAVOR
from canonical.testing.layers import DatabaseFunctionalLayer


class TestBranchCloud(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        remove_all_sample_data_branches()
        self._branch_cloud = getUtility(IBranchCloud)

    def getProductsWithInfo(self, num_products=None):
        """Get product cloud information."""
        # We use the MASTER_FLAVOR so that data changes made in these tests
        # are visible to the query in getProductsWithInfo. The default
        # implementation uses the SLAVE_FLAVOR.
        return self._branch_cloud.getProductsWithInfo(
            num_products, store_flavor=MASTER_FLAVOR)

    def makeBranch(self, product=None, branch_type=None,
                   last_commit_date=None, private=False):
        """Make a product branch with a particular last commit date"""
        revision_count = 5
        delta = timedelta(days=1)
        if last_commit_date is None:
            date_generator = None
        else:
            start_date = last_commit_date - delta * (revision_count - 1)
            # The output of getProductsWithInfo doesn't include timezone
            # information -- not sure why. To make the tests a little clearer,
            # this method expects last_commit_date to be a naive datetime that
            # can be compared directly with the output of getProductsWithInfo.
            start_date = start_date.replace(tzinfo=pytz.UTC)
            date_generator = time_counter(start_date, delta)
        branch = self.factory.makeProductBranch(
            product=product, branch_type=branch_type, private=private)
        self.factory.makeRevisionsForBranch(
            removeSecurityProxy(branch), count=revision_count,
            date_generator=date_generator)
        return branch

    def test_empty_with_no_branches(self):
        # getProductsWithInfo returns an empty result set if there are no
        # branches in the database.
        products_with_info = self.getProductsWithInfo()
        self.assertEqual([], list(products_with_info))

    def test_empty_products_not_counted(self):
        # getProductsWithInfo doesn't include products that don't have any
        # branches.
        #
        # Note that this is tested implicitly by test_empty_with_no_branches,
        # since there are such products in the sample data.
        product = self.factory.makeProduct()
        products_with_info = self.getProductsWithInfo()
        self.assertEqual([], list(products_with_info))

    def test_empty_branches_not_counted(self):
        # getProductsWithInfo doesn't consider branches that lack revision
        # data, 'empty branches', to contribute to the count of branches on a
        # product.
        branch = self.factory.makeProductBranch()
        products_with_info = self.getProductsWithInfo()
        self.assertEqual([], list(products_with_info))

    def test_import_branches_not_counted(self):
        # getProductsWithInfo doesn't consider imported branches to contribute
        # to the count of branches on a product.
        branch = self.makeBranch(branch_type=BranchType.IMPORTED)
        products_with_info = self.getProductsWithInfo()
        self.assertEqual([], list(products_with_info))

    def test_remote_branches_not_counted(self):
        # getProductsWithInfo doesn't consider remote branches to contribute
        # to the count of branches on a product.
        branch = self.makeBranch(branch_type=BranchType.REMOTE)
        products_with_info = self.getProductsWithInfo()
        self.assertEqual([], list(products_with_info))

    def test_private_branches_not_counted(self):
        # getProductsWithInfo doesn't count private branches.
        branch = self.makeBranch(private=True)
        products_with_info = self.getProductsWithInfo()
        self.assertEqual([], list(products_with_info))

    def test_hosted_and_mirrored_counted(self):
        # getProductsWithInfo includes products that have hosted or mirrored
        # branches with revisions.
        product = self.factory.makeProduct()
        self.makeBranch(product=product, branch_type=BranchType.HOSTED)
        last_commit_date = datetime(2007, 1, 5)
        self.makeBranch(
            product=product, branch_type=BranchType.MIRRORED,
            last_commit_date=last_commit_date)
        products_with_info = self.getProductsWithInfo()
        self.assertEqual(
            [(product.name, 2, last_commit_date)], list(products_with_info))

    def test_includes_products_with_branches_with_revisions(self):
        # getProductsWithInfo includes all products that have branches with
        # revisions.
        last_commit_date = datetime(2008, 12, 25)
        branch = self.makeBranch(last_commit_date=last_commit_date)
        products_with_info = self.getProductsWithInfo()
        self.assertEqual(
            [(branch.product.name, 1, last_commit_date)],
            list(products_with_info))

    def test_uses_latest_revision_date(self):
        # getProductsWithInfo uses the most recent revision date from all the
        # branches in that product.
        product = self.factory.makeProduct()
        self.makeBranch(
            product=product, last_commit_date=datetime(2008, 12, 25))
        last_commit_date = datetime(2009, 01, 01)
        self.makeBranch(product=product, last_commit_date=last_commit_date)
        products_with_info = self.getProductsWithInfo()
        self.assertEqual(
            [(product.name, 2, last_commit_date)], list(products_with_info))

    def test_sorted_by_branch_count(self):
        # getProductsWithInfo returns a result set sorted so that the products
        # with the most branches come first.
        product1 = self.factory.makeProduct()
        for i in range(3):
            self.makeBranch(product=product1)
        product2 = self.factory.makeProduct()
        for i in range(5):
            self.makeBranch(product=product2)
        self.assertEqual(
            [product2.name, product1.name],
            [name for name, count, last_commit
             in self.getProductsWithInfo()])

    def test_limit(self):
        # If num_products is passed to getProductsWithInfo, it limits the
        # number of products in the result set. The products with the fewest
        # branches are discarded first.
        product1 = self.factory.makeProduct()
        for i in range(3):
            self.makeBranch(product=product1)
        product2 = self.factory.makeProduct()
        for i in range(5):
            self.makeBranch(product=product2)
        product3 = self.factory.makeProduct()
        for i in range(7):
            self.makeBranch(product=product3)
        self.assertEqual(
            [product3.name, product2.name],
            [name for name, count, last_commit
             in self.getProductsWithInfo(num_products=2)])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

