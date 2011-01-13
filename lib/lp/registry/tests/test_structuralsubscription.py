# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `StructuralSubscription`."""

__metaclass__ = type

from zope.security.interfaces import Unauthorized

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.bugs.model.bugsubscriptionfilter import BugSubscriptionFilter
from lp.testing import (
    anonymous_logged_in,
    person_logged_in,
    TestCaseWithFactory,
    )


class TestStructuralSubscription(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_bug_filters_empty(self):
        # StructuralSubscription.filters returns the BugSubscriptionFilter
        # records associated with this subscription. It's empty to begin with.
        product = self.factory.makeProduct()
        with person_logged_in(product.owner):
            subscription = product.addSubscription(
                product.owner, product.owner)
        self.assertEqual([], list(subscription.bug_filters))

    def test_bug_filters(self):
        # StructuralSubscription.filters returns the BugSubscriptionFilter
        # records associated with this subscription.
        product = self.factory.makeProduct()
        with person_logged_in(product.owner):
            subscription = product.addSubscription(
                product.owner, product.owner)
            subscription_filter = BugSubscriptionFilter()
            subscription_filter.structural_subscription = subscription
        self.assertEqual([subscription_filter], list(subscription.bug_filters))

    def test_newBugFilter(self):
        # StructuralSubscription.newBugFilter() creates a new subscription
        # filter linked to the subscription.
        product = self.factory.makeProduct()
        with person_logged_in(product.owner):
            subscription = product.addSubscription(
                product.owner, product.owner)
            subscription_filter = subscription.newBugFilter()
        self.assertEqual(
            subscription, subscription_filter.structural_subscription)
        self.assertEqual([subscription_filter], list(subscription.bug_filters))

    def test_newBugFilter_only_for_subscriber(self):
        # StructuralSubscription.newBugFilter() can only be called by the
        # subscriber.
        product = self.factory.makeProduct()
        with person_logged_in(product.owner):
            subscription = product.addSubscription(
                product.owner, product.owner)
        with anonymous_logged_in():
            self.assertRaises(
                Unauthorized, lambda: subscription.newBugFilter)
        with person_logged_in(self.factory.makePerson()):
            self.assertRaises(
                Unauthorized, lambda: subscription.newBugFilter)
