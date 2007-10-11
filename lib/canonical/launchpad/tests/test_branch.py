# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Unit tests for Branch related functions."""

import unittest

from canonical.launchpad.database import Branch, BranchSet
from canonical.launchpad.interfaces import BranchListingSort

class TestListingToSortOrder(unittest.TestCase):
    def assertColumnNotReferenced(self, column, order_by_list):
        self.failIf(column in order_by_list or '-'+column in order_by_list)

    def test_default(self):
        self.assertEquals(BranchSet._listingSortToOrderBy(None),
                          Branch._defaultOrder)

    def test_lifecycle(self):
        lifecycle_order = BranchSet._listingSortToOrderBy(
            BranchListingSort.LIFECYCLE)
        self.assertEquals(lifecycle_order[0], '-lifecycle')
        self.assertColumnNotReferenced('lifecycle', lifecycle_order[1:])

    def test_registrant(self):
        self.assertColumnNotReferenced('owner', Branch._defaultOrder)
        registrant_order = BranchSet._listingSortToOrderBy(
            BranchListingSort.REGISTRANT)
        self.assertEquals(registrant_order[0], 'owner')
        self.assertEquals(registrant_order[1:], Branch._defaultOrder)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
