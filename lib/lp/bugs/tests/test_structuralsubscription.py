# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `StructuralSubscription`."""

__metaclass__ = type

from storm.store import Store
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
        self.original_filter = self.subscription.bug_filters[0]

    def test_delete_requires_Edit_permission(self):
        # delete() is only available to the subscriber.
        # We use a lambda here because a security proxy around
        # self.subscription is giving us the behavior we want to
        # demonstrate.  Merely accessing the "delete" name raises
        # Unauthorized, before the method is even called.  Therefore,
        # we use a lambda to make the trigger happen within "assertRaises".
        with anonymous_logged_in():
            self.assertRaises(Unauthorized, lambda: self.subscription.delete)
        with person_logged_in(self.factory.makePerson()):
            self.assertRaises(Unauthorized, lambda: self.subscription.delete)

    def test_simple_delete(self):
        with person_logged_in(self.product.owner):
            self.subscription.delete()
            self.assertEqual(
                self.product.getSubscription(self.product.owner), None)

    def test_delete_cascades_to_filters(self):
        with person_logged_in(self.product.owner):
            subscription_id = self.subscription.id
            self.subscription.newBugFilter()
            self.subscription.delete()
            self.assertEqual(
                self.product.getSubscription(self.product.owner), None)
            store = Store.of(self.product)
            # We know that the filter is gone, because we know the
            # subscription is gone, and the database would have
            # prevented the deletion of a subscription without first
            # deleting the filters.  We'll double-check, to be sure.
            self.assertEqual(
                store.find(
                    BugSubscriptionFilter,
                    BugSubscriptionFilter.structural_subscription_id ==
                        subscription_id).one(),
                None)

    def test_bug_filters_default(self):
        # The bug_filters attribute has a default empty bug filter
        # to begin with.
        self.assertEqual([self.original_filter],
                         list(self.subscription.bug_filters))

    def test_bug_filters(self):
        # The bug_filters attribute returns the BugSubscriptionFilter records
        # associated with this subscription.
        subscription_filter = BugSubscriptionFilter()
        subscription_filter.structural_subscription = self.subscription
        self.assertContentEqual(
            [subscription_filter, self.original_filter],
            list(self.subscription.bug_filters))

    def test_newBugFilter(self):
        # newBugFilter() creates a new subscription filter linked to the
        # subscription.
        with person_logged_in(self.product.owner):
            subscription_filter = self.subscription.newBugFilter()
        self.assertEqual(
            self.subscription,
            subscription_filter.structural_subscription)
        self.assertContentEqual(
            [subscription_filter, self.original_filter],
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
