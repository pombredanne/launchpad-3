# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests from branch subset."""

__metaclass__ = type

import unittest

from canonical.launchpad.database.branchsubset import ProductBranchSubset
from canonical.launchpad.interfaces.branchsubset import IBranchSubset
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.testing.layers import DatabaseFunctionalLayer


class TestProductBranchSubset(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_provides_interface(self):
        self.assertProvides(
            ProductBranchSubset(self.factory.makeProduct()), IBranchSubset)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

