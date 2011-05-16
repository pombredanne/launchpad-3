# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for product series views."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.browser.productseries import ProductSeriesNavigation
from lp.testing import TestCaseWithFactory


class ProductSeriesNavigationTestCase(TestCaseWithFactory):
    """Test ProductSeriesNavigation."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(ProductSeriesNavigationTestCase, self).setUp()
        self.product_series = self.factory.makeProductSeries()

    def test_traverse_match(self):
        # The release is returned when the name matches a version.
        milestone = self.factory.makeMilestone(
            name='0.0.1', productseries=self.product_series)
        release = self.factory.makeProductRelease(milestone=milestone)
        navigation = ProductSeriesNavigation(self.product_series)
        self.assertEqual(release, navigation.traverse('0.0.1'))

    def test_traverse_none(self):
        # None is returned when the name does not matches a version.
        self.factory.makeMilestone(
            name='0.0.1', productseries=self.product_series)
        navigation = ProductSeriesNavigation(self.product_series)
        self.assertEqual(None, navigation.traverse('0.0.1'))
