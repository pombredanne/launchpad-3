# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the bugsubscription module."""

__metaclass__ = type

from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.testing import DatabaseFunctionalLayer
from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskStatus,
    )
from lp.bugs.model.bugsubscription import (
    BugSubscriptionFilter,
    BugSubscriptionFilterImportance,
    BugSubscriptionFilterStatus,
    )
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )


class TestBugSubscriptionFilter(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugSubscriptionFilter, self).setUp()
        self.target = self.factory.makeProduct()
        self.subscriber = self.target.owner
        login_person(self.subscriber)
        self.subscription = self.target.addBugSubscription(
            self.subscriber, self.subscriber)

    def test_basics(self):
        """Test the basic operation of `BugSubscriptionFilter` objects."""
        # Create.
        bug_subscription_filter = BugSubscriptionFilter()
        bug_subscription_filter.structural_subscription = self.subscription
        bug_subscription_filter.find_all_tags = True
        bug_subscription_filter.include_any_tags = True
        bug_subscription_filter.exclude_any_tags = True
        bug_subscription_filter.other_parameters = u"foo"
        bug_subscription_filter.description = u"bar"
        # Flush and reload.
        IStore(bug_subscription_filter).flush()
        IStore(bug_subscription_filter).reload(bug_subscription_filter)
        # Check.
        self.assertIsNot(None, bug_subscription_filter.id)
        self.assertEqual(
            self.subscription.id,
            bug_subscription_filter.structural_subscription_id)
        self.assertEqual(
            self.subscription,
            bug_subscription_filter.structural_subscription)
        self.assertIs(True, bug_subscription_filter.find_all_tags)
        self.assertIs(True, bug_subscription_filter.include_any_tags)
        self.assertIs(True, bug_subscription_filter.exclude_any_tags)
        self.assertEqual(u"foo", bug_subscription_filter.other_parameters)
        self.assertEqual(u"bar", bug_subscription_filter.description)

    def test_defaults(self):
        """Test the default values of `BugSubscriptionFilter` objects."""
        # Create.
        bug_subscription_filter = BugSubscriptionFilter()
        bug_subscription_filter.structural_subscription = self.subscription
        # Check.
        self.assertIs(False, bug_subscription_filter.find_all_tags)
        self.assertIs(False, bug_subscription_filter.find_all_tags)
        self.assertIs(False, bug_subscription_filter.include_any_tags)
        self.assertIs(False, bug_subscription_filter.exclude_any_tags)
        self.assertIs(None, bug_subscription_filter.other_parameters)
        self.assertIs(None, bug_subscription_filter.description)


class TestBugSubscriptionFilterStatus(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugSubscriptionFilterStatus, self).setUp()
        self.target = self.factory.makeProduct()
        self.subscriber = self.target.owner
        login_person(self.subscriber)
        self.subscription = self.target.addBugSubscription(
            self.subscriber, self.subscriber)
        self.subscription_filter = BugSubscriptionFilter()
        self.subscription_filter.structural_subscription = self.subscription

    def test_basics(self):
        """Test the basics of `BugSubscriptionFilterStatus` objects."""
        # Create.
        bug_sub_filter_status = BugSubscriptionFilterStatus()
        bug_sub_filter_status.filter = self.subscription_filter
        bug_sub_filter_status.status = BugTaskStatus.NEW
        # Flush and reload.
        IStore(bug_sub_filter_status).flush()
        IStore(bug_sub_filter_status).reload(bug_sub_filter_status)
        # Check.
        self.assertIsNot(None, bug_sub_filter_status.id)
        self.assertEqual(
            self.subscription_filter.id,
            bug_sub_filter_status.filter_id)
        self.assertEqual(
            self.subscription_filter,
            bug_sub_filter_status.filter)
        self.assertEqual(BugTaskStatus.NEW, bug_sub_filter_status.status)


class TestBugSubscriptionFilterImportance(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugSubscriptionFilterImportance, self).setUp()
        self.target = self.factory.makeProduct()
        self.subscriber = self.target.owner
        login_person(self.subscriber)
        self.subscription = self.target.addBugSubscription(
            self.subscriber, self.subscriber)
        self.subscription_filter = BugSubscriptionFilter()
        self.subscription_filter.structural_subscription = self.subscription

    def test_basics(self):
        """Test the basics of `BugSubscriptionFilterImportance` objects."""
        # Create.
        bug_sub_filter_importance = BugSubscriptionFilterImportance()
        bug_sub_filter_importance.filter = self.subscription_filter
        bug_sub_filter_importance.importance = BugTaskImportance.HIGH
        # Flush and reload.
        IStore(bug_sub_filter_importance).flush()
        IStore(bug_sub_filter_importance).reload(bug_sub_filter_importance)
        # Check.
        self.assertIsNot(None, bug_sub_filter_importance.id)
        self.assertEqual(
            self.subscription_filter.id,
            bug_sub_filter_importance.filter_id)
        self.assertEqual(
            self.subscription_filter,
            bug_sub_filter_importance.filter)
        self.assertEqual(
            BugTaskImportance.HIGH,
            bug_sub_filter_importance.importance)
