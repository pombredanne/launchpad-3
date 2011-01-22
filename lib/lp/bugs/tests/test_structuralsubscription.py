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

    def setUp(self):
        super(TestStructuralSubscription, self).setUp()
        self.product = self.factory.makeProduct()
        with person_logged_in(self.product.owner):
            self.subscription = self.product.addSubscription(
                self.product.owner, self.product.owner)

    def test_bug_filters_empty(self):
        # The bug_filters attribute is empty to begin with.
        self.assertEqual([], list(self.subscription.bug_filters))

    def test_bug_filters(self):
        # The bug_filters attribute returns the BugSubscriptionFilter records
        # associated with this subscription.
        subscription_filter = BugSubscriptionFilter()
        subscription_filter.structural_subscription = self.subscription
        self.assertEqual(
            [subscription_filter],
            list(self.subscription.bug_filters))

    def test_newBugFilter(self):
        # newBugFilter() creates a new subscription filter linked to the
        # subscription.
        with person_logged_in(self.product.owner):
            subscription_filter = self.subscription.newBugFilter()
        self.assertEqual(
            self.subscription,
            subscription_filter.structural_subscription)
        self.assertEqual(
            [subscription_filter],
            list(self.subscription.bug_filters))

    def test_newBugFilter_by_anonymous(self):
        # newBugFilter() is not available to anonymous users.
        with anonymous_logged_in():
            self.assertRaises(
                Unauthorized, lambda: self.subscription.newBugFilter)

    def test_newBugFilter_by_other_user(self):
        # newBugFilter() is only available to the subscriber.
        with person_logged_in(self.factory.makePerson()):
            self.assertRaises(
                Unauthorized, lambda: self.subscription.newBugFilter)
