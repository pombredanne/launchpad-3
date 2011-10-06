# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the bugsubscription module."""

__metaclass__ = type

from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.testing import DatabaseFunctionalLayer
from lp.bugs.interfaces.bugtask import BugTaskStatus
from lp.bugs.model.bugsubscriptionfilter import BugSubscriptionFilter
from lp.bugs.model.bugsubscriptionfilterstatus import (
    BugSubscriptionFilterStatus,
    )
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )


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
