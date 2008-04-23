# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for ProductSeries."""

__metaclass__ = type


from unittest import TestCase, TestLoader

from zope.component import getUtility

from canonical.launchpad.ftests import login, logout, syncUpdate
from canonical.launchpad.database.productseries import ProductSeriesSet
from canonical.launchpad.interfaces import BranchType, ILaunchpadCelebrities
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.testing import LaunchpadFunctionalLayer


class TestProductSeriesForBranches(TestCase):
    """Test getting series associated with branches."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCase.setUp(self)
        # Log in an admin as we are setting series branches, which is a
        # protected activity.
        login('foo.bar@canonical.com')
        self.factory = LaunchpadObjectFactory()
        self.product = self.factory.makeProduct()
        self.branches = [
            self.factory.makeBranch(product=self.product) for x in range(3)]

    def tearDown(self):
        logout()
        TestCase.tearDown(self)

    def test_no_series_set(self):
        """If there are no series branches."""
        self.assertEqual(
            [], list(ProductSeriesSet().getSeriesForBranches(self.branches)))

    def test_current_dev_focus(self):
        """A series with a branch associated is returned."""
        dev_focus = self.product.development_focus
        dev_focus.user_branch = self.branches[0]
        syncUpdate(dev_focus)
        self.assertEqual(
            [self.product.development_focus],
            list(ProductSeriesSet().getSeriesForBranches(self.branches)))

    def test_result_ordering(self):
        """Series are ordered alphabetically in the results."""
        gamma = self.product.newSeries(
            self.product.owner, "gamma", "summary", self.branches[0])
        beta = self.product.newSeries(
            self.product.owner, "beta", "summary", self.branches[1])
        alpha = self.product.newSeries(
            self.product.owner, "alpha", "summary", self.branches[2])
        self.assertEqual(
            [alpha, beta, gamma],
            list(ProductSeriesSet().getSeriesForBranches(self.branches)))

    def test_multiple_series_for_single_branch(self):
        """A single branch can be assiciated with multiple series.

        Make sure that all the associated series get returned.
        """
        branch = self.branches[0]
        gamma = self.product.newSeries(
            self.product.owner, "gamma", "summary", branch)
        beta = self.product.newSeries(
            self.product.owner, "beta", "summary", branch)
        alpha = self.product.newSeries(
            self.product.owner, "alpha", "summary", branch)
        self.assertEqual(
            [alpha, beta, gamma],
            list(ProductSeriesSet().getSeriesForBranches(self.branches)))

    def test_non_associated_series_not_returned(self):
        """Only series with associated branches are returned."""
        branch = self.branches[0]
        gamma = self.product.newSeries(
            self.product.owner, "gamma", "summary", branch)
        beta = self.product.newSeries(
            self.product.owner, "beta", "summary")
        self.assertEqual(
            [gamma],
            list(ProductSeriesSet().getSeriesForBranches(self.branches)))

    def test_import_branches_also_linked(self):
        """Series with import branches are returned."""
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        branch = self.factory.makeBranch(
            owner=vcs_imports, product=self.product,
            branch_type=BranchType.IMPORTED)
        dev_focus = self.product.development_focus
        dev_focus.import_branch = branch
        syncUpdate(dev_focus)
        self.assertEqual(
            [dev_focus],
            list(ProductSeriesSet().getSeriesForBranches([branch])))


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
