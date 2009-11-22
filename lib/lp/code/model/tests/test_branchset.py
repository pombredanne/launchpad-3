# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BranchSet."""

__metaclass__ = type

from unittest import TestLoader

from lp.code.model.branch import BranchSet
from lp.code.enums import BranchLifecycleStatus
from lp.registry.interfaces.product import IProductSet
from lp.testing import TestCaseWithFactory
from canonical.testing import DatabaseFunctionalLayer

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy


class TestBranchSet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.product = getUtility(IProductSet).getByName('firefox')
        self.branch_set = BranchSet()

    def test_limitedByQuantity(self):
        """When getting the latest branches for a product, we can specify the
        maximum number of branches we want to know about.
        """
        quantity = 3
        latest_branches = self.branch_set.getLatestBranchesForProduct(
            self.product, quantity)
        self.assertEqual(quantity, len(list(latest_branches)))

    def test_onlyForProduct(self):
        """getLatestBranchesForProduct returns branches only from the
        requested product.
        """
        quantity = 5
        latest_branches = self.branch_set.getLatestBranchesForProduct(
            self.product, quantity)
        self.assertEqual(
            [self.product.name] * quantity,
            [branch.product.name for branch in latest_branches])

    def test_abandonedBranchesNotIncluded(self):
        """getLatestBranchesForProduct does not include branches that have
        been abandoned, because they are not relevant for those interested
        in recent activity.
        """
        original_branches = list(
            self.branch_set.getLatestBranchesForProduct(self.product, 5))
        branch = original_branches[0]
        # XXX: JonathanLange 2007-07-06: WHITEBOXING. The anonymous user
        # cannot change branch details, so we remove the security proxy and
        # change it.
        branch = removeSecurityProxy(branch)
        branch.lifecycle_status = BranchLifecycleStatus.ABANDONED
        latest_branches = list(
            self.branch_set.getLatestBranchesForProduct(self.product, 5))
        self.assertEqual(original_branches[1:], latest_branches)

    def test_getByUrls(self):
        # getByUrls returns a list of branches matching the list of URLs that
        # it's given.
        a = self.factory.makeAnyBranch()
        b = self.factory.makeAnyBranch()
        branches = self.branch_set.getByUrls(
            [a.bzr_identity, b.bzr_identity])
        self.assertEqual({a.bzr_identity: a, b.bzr_identity: b}, branches)

    def test_getByUrls_cant_find_url(self):
        # If a branch cannot be found for a URL, then None appears in the list
        # in place of the branch.
        url = 'http://example.com/doesntexist'
        branches = self.branch_set.getByUrls([url])
        self.assertEqual({url: None}, branches)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
