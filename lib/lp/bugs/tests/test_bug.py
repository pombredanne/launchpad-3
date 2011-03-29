# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.bugs.model.Bug."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer

from lp.bugs.enum import BugNotificationLevel
from lp.testing import (
    feature_flags,
    person_logged_in,
    set_feature_flag,
    TestCaseWithFactory,
    )

class TestBugSubscriptionMethods(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugSubscriptionMethods, self).setUp()
        self.bug = self.factory.makeBug()
        self.person = self.factory.makePerson()

    def test_is_muted_returns_true_for_muted_users(self):
        # Bug.isMuted() will return True if the passed to it has a
        # BugSubscription with a BugNotificationLevel of NOTHING.
        with person_logged_in(self.person):
            subscription = self.bug.subscribe(
                self.person, self.person, level=BugNotificationLevel.NOTHING)
            self.assertEqual(True, self.bug.isMuted(self.person))

    def test_is_muted_returns_false_for_direct_subscribers(self):
        # Bug.isMuted() will return False if the user has a subscription
        # with BugNotificationLevel that's not NOTHING.
        with person_logged_in(self.person):
            subscription = self.bug.subscribe(
                self.person, self.person, level=BugNotificationLevel.METADATA)
            self.assertEqual(False, self.bug.isMuted(self.person))

    def test_is_muted_returns_false_for_non_subscribers(self):
        # Bug.isMuted() will return False if the user has no
        # subscription.
        with person_logged_in(self.person):
            self.assertEqual(False, self.bug.isMuted(self.person))

    def test_mute_mutes_user(self):
        # Bug.mute() adds a muted subscription for the user passed to
        # it.
        with person_logged_in(self.person):
            muted_subscription = self.bug.mute(
                self.person, self.person)
            self.assertEqual(
                BugNotificationLevel.NOTHING,
                muted_subscription.bug_notification_level)

    def test_mute_mutes_user_with_existing_subscription(self):
        # Bug.mute() will update an existing subscription so that it
        # becomes muted.
        with person_logged_in(self.person):
            subscription = self.bug.subscribe(self.person, self.person)
            muted_subscription = self.bug.mute(self.person, self.person)
            self.assertEqual(subscription, muted_subscription)
            self.assertEqual(
                BugNotificationLevel.NOTHING,
                subscription.bug_notification_level)

    def test_unmute_unmutes_user(self):
        # Bug.unmute() will remove a muted subscription for the user
        # passed to it.
        with person_logged_in(self.person):
            self.bug.mute(self.person, self.person)
            self.assertTrue(self.bug.isMuted(self.person))
            self.bug.unmute(self.person, self.person)
            self.assertFalse(self.bug.isMuted(self.person))
