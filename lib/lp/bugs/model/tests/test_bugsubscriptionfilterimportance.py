# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the bugsubscription module."""

__metaclass__ = type

from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.testing import DatabaseFunctionalLayer
from lp.bugs.interfaces.bugtask import BugTaskImportance
from lp.bugs.model.bugsubscriptionfilter import BugSubscriptionFilter
from lp.bugs.model.bugsubscriptionfilterimportance import (
    BugSubscriptionFilterImportance,
    )
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )


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
