# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Unit tests for methods of Branch and BranchSet."""

import unittest

from canonical.launchpad.database.branch import (
    BranchSet, DEFAULT_BRANCH_LISTING_SORT)
from canonical.launchpad.interfaces import BranchListingSort


class TestListingToSortOrder(unittest.TestCase):
    """Tests for the BranchSet._listingSortToOrderBy static method.

    This method translates values from the BranchListingSort enumeration into
    values suitable to pass to orderBy in queries against BranchWithSortKeys.
    """

    def assertColumnNotReferenced(self, column, order_by_list):
        """Ensure that column is not referenced in any way in order_by_list.
        """
        self.failIf(column in order_by_list or
                    ('-' + column) in order_by_list)

    def test_default(self):
        """Test that passing None results in the default list."""
        self.assertEquals(BranchSet._listingSortToOrderBy(None),
                          DEFAULT_BRANCH_LISTING_SORT)

    def test_lifecycle(self):
        """Test with an option that's part of the default sort.

        Sorting on LIFECYCYLE moves the lifecycle reference to the
        first element of the output."""
        # Check that this isn't a no-op.
        self.assertNotEquals(DEFAULT_BRANCH_LISTING_SORT[0],
                             '-lifecycle_status')
        lifecycle_order = BranchSet._listingSortToOrderBy(
            BranchListingSort.LIFECYCLE)
        self.assertEquals(lifecycle_order[0], '-lifecycle_status')
        # Check that no reference to lifecycle remains in the list
        self.assertColumnNotReferenced('lifecycle_status', lifecycle_order[1:])

    def test_sortOnColumNotInDefaultSortOrder(self):
        """Test with an option that's not part of the default sort.

        This should put the passed option first in the list, but leave
        the rest the same.
        """
        self.assertColumnNotReferenced(
            'owner.name', DEFAULT_BRANCH_LISTING_SORT)
        registrant_order = BranchSet._listingSortToOrderBy(
            BranchListingSort.REGISTRANT)
        self.assertEquals(registrant_order[0], 'owner.name')
        self.assertEquals(registrant_order[1:], DEFAULT_BRANCH_LISTING_SORT)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
