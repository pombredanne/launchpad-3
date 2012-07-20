# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test IStructuralSubscription adapters"""

__metaclass__ = type

from lp.bugs.adapters.bugsubscriptionfilter import (
    subscription_to_distribution,
    subscription_to_product,
    )
from lp.bugs.model.bugsubscriptionfilter import BugSubscriptionFilter
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.product import IProduct
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class BugSubscriptionFilterTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_subscription_to_product_with_product(self):
        product = self.factory.makeProduct()
        subscriber = product.owner
        login_person(subscriber)
        subscription = product.addBugSubscription(subscriber, subscriber)
        subscription_filter = BugSubscriptionFilter()
        subscription_filter.structuralsubscription = subscription
        self.assertEqual(product, subscription_to_product(subscription_filter))
        self.assertEqual(product, IProduct(subscription_filter))

    def test_subscription_to_product_with_productseries(self):
        product = self.factory.makeProduct()
        series = product.development_focus
        subscriber = product.owner
        login_person(subscriber)
        subscription = series.addBugSubscription(subscriber, subscriber)
        subscription_filter = BugSubscriptionFilter()
        subscription_filter.structuralsubscription = subscription
        self.assertEqual(product, subscription_to_product(subscription_filter))
        self.assertEqual(product, IProduct(subscription_filter))

    def test_subscription_to_distribution_with_distribution(self):
        distribution = self.factory.makeDistribution()
        subscriber = distribution.owner
        login_person(subscriber)
        subscription = distribution.addBugSubscription(subscriber, subscriber)
        subscription_filter = BugSubscriptionFilter()
        subscription_filter.structuralsubscription = subscription
        self.assertEqual(
            distribution, subscription_to_distribution(subscription_filter))
        self.assertEqual(distribution, IDistribution(subscription_filter))

    def test_subscription_to_distroseries_with_distribution(self):
        distribution = self.factory.makeDistribution()
        series = self.factory.makeDistroSeries(distribution=distribution)
        subscriber = distribution.owner
        login_person(subscriber)
        subscription = series.addBugSubscription(subscriber, subscriber)
        subscription_filter = BugSubscriptionFilter()
        subscription_filter.structuralsubscription = subscription
        self.assertEqual(
            distribution, subscription_to_distribution(subscription_filter))
        self.assertEqual(distribution, IDistribution(subscription_filter))
