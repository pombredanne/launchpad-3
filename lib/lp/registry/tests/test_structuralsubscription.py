# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `StructuralSubscription`."""

__metaclass__ = type

from canonical.testing.layers import LaunchpadZopelessLayer
from lp.bugs.model.bugsubscriptionfilter import BugSubscriptionFilter
from lp.testing import TestCaseWithFactory


class TestStructuralSubscription(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_bug_filters_empty(self):
        # StructuralSubscription.filters returns the BugSubscriptionFilter
        # records associated with this subscription. It's empty to begin with.
        product = self.factory.makeProduct()
        subscription = product.addSubscription(product.owner, product.owner)
        self.assertEqual([], list(subscription.bug_filters))

    def test_bug_filters(self):
        # StructuralSubscription.filters returns the BugSubscriptionFilter
        # records associated with this subscription.
        product = self.factory.makeProduct()
        subscription = product.addSubscription(product.owner, product.owner)
        subscription_filter = BugSubscriptionFilter()
        subscription_filter.structural_subscription = subscription
        self.assertEqual([subscription_filter], list(subscription.bug_filters))

    def test_newBugFilter(self):
        # Structural_Subscription.newBugFilter() creates a new subscription
        # filter linked to the subscription.
        product = self.factory.makeProduct()
        subscription = product.addSubscription(product.owner, product.owner)
        subscription_filter = subscription.newBugFilter()
        self.assertEqual(
            subscription, subscription_filter.structural_subscription)
        self.assertEqual([subscription_filter], list(subscription.bug_filters))
