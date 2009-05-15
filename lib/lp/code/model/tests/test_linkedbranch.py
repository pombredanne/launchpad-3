# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for linked branch implementations."""

__metaclass__ = type


import unittest

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.code.interfaces.linkedbranch import ICanHasLinkedBranch
from lp.testing import TestCaseWithFactory


class TestLinkedBranch(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_product_series(self):
        # The linked branch of a product series is its branch attribute.
        product_series = self.factory.makeProductSeries()
        product_series.branch = self.factory.makeProductBranch(
            product=product_series.product)
        self.assertEqual(
            product_series.branch, ICanHasLinkedBranch(product_series).branch)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
