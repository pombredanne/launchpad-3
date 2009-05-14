# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for branch listing."""

__metaclass__ = type

import unittest

from storm.expr import Asc, Desc

from lp.code.browser.branchlisting import (
    BranchListingSort, BranchListingView, SourcePackageBranchesView)
from lp.code.model.branch import Branch
from lp.registry.model.person import Owner
from lp.registry.model.product import Product
from lp.testing import TestCase, TestCaseWithFactory
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer


class TestListingToSortOrder(TestCase):
    """Tests for the BranchSet._listingSortToOrderBy static method.

    This method translates values from the BranchListingSort enumeration into
    values suitable to pass to orderBy in queries against BranchWithSortKeys.
    """

    DEFAULT_BRANCH_LISTING_SORT = [
        Asc(Product.name),
        Desc(Branch.lifecycle_status),
        Asc(Owner.name),
        Asc(Branch.name),
        ]

    def assertColumnNotReferenced(self, column, order_by_list):
        """Ensure that column is not referenced in any way in order_by_list.
        """
        self.failIf(column in order_by_list or
                    ('-' + column) in order_by_list)

    def assertSortsEqual(self, sort_one, sort_two):
        """Assert that one list of sort specs is equal to another."""
        def sort_data(sort):
            return sort.suffix, sort.expr
        self.assertEqual(map(sort_data, sort_one), map(sort_data, sort_two))

    def test_default(self):
        """Test that passing None results in the default list."""
        self.assertSortsEqual(
            self.DEFAULT_BRANCH_LISTING_SORT,
            BranchListingView._listingSortToOrderBy(None))

    def test_lifecycle(self):
        """Test with an option that's part of the default sort.

        Sorting on LIFECYCYLE moves the lifecycle reference to the
        first element of the output."""
        # Check that this isn't a no-op.
        lifecycle_order = BranchListingView._listingSortToOrderBy(
            BranchListingSort.LIFECYCLE)
        self.assertSortsEqual(
            [Desc(Branch.lifecycle_status),
             Asc(Product.name),
             Asc(Owner.name),
             Asc(Branch.name)], lifecycle_order)

    def test_sortOnColumNotInDefaultSortOrder(self):
        """Test with an option that's not part of the default sort.

        This should put the passed option first in the list, but leave
        the rest the same.
        """
        registrant_order = BranchListingView._listingSortToOrderBy(
            BranchListingSort.OLDEST_FIRST)
        self.assertSortsEqual(
            [Asc(Branch.date_created)] + self.DEFAULT_BRANCH_LISTING_SORT,
            registrant_order)


class TestSourcePackageBranchesView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_distroseries_links(self):
        # There are some links at the bottom of the page to other
        # distroseries.
        distro = self.factory.makeDistribution()
        sourcepackagename = self.factory.makeSourcePackageName()
        packages = {}
        for version in ("1.0", "2.0", "3.0"):
            series = self.factory.makeDistroRelease(
                distribution=distro, version=version)
            package = self.factory.makeSourcePackage(
                distroseries=series, sourcepackagename=sourcepackagename)
            packages[version] = package
        request = LaunchpadTestRequest()
        view = SourcePackageBranchesView(packages["2.0"], request)
        self.assertEqual(
            [dict(series_name=packages["1.0"].distroseries.name,
                  package=packages["1.0"], linked=True),
             dict(series_name=packages["2.0"].distroseries.name,
                  package=packages["2.0"], linked=False),
             dict(series_name=packages["3.0"].distroseries.name,
                  package=packages["3.0"], linked=True)],
            list(view.series_links))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

