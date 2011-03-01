# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for adapters."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.adapters import (
    distroseries_to_distribution,
    productseries_to_product,
    )
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.product import IProduct
from lp.testing import TestCaseWithFactory


class TestAdapters(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_distroseries_to_distribution(self):
        # distroseries_to_distribution() returns an IDistribution given an
        # IDistroSeries.
        distro_series = self.factory.makeDistroSeries()
        distribution = distroseries_to_distribution(distro_series)
        self.assertTrue(IDistribution.providedBy(distribution))

    def test_distroseries_to_distribution_adapter(self):
        # distroseries_to_distribution() is registered as an adapter from
        # IDistroSeries to IDistribution.
        distro_series = self.factory.makeDistroSeries()
        distribution = IDistribution(distro_series)
        self.assertTrue(IDistribution.providedBy(distribution))

    def test_productseries_to_product(self):
        # productseries_to_product() returns an IProduct given an
        # IProductSeries.
        product_series = self.factory.makeProductSeries()
        product = productseries_to_product(product_series)
        self.assertTrue(IProduct.providedBy(product))

    def test_productseries_to_product_adapter(self):
        # productseries_to_product() is registered as an adapter from
        # IProductSeries to IProduct.
        product_series = self.factory.makeProductSeries()
        product = IProduct(product_series)
        self.assertTrue(IProduct.providedBy(product))
