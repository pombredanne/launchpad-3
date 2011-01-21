# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BugSubscriptions."""

__metaclass__ = type

from zope.security.interfaces import Unauthorized

from canonical.testing.layers import DatabaseFunctionalLayer

from lp.registry.enum import BugNotificationLevel
from lp.registry.interfaces.teammembership import TeamMembershipStatus
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


class TestBugSubscription(TestCaseWithFactory):
    """Tests for the `BugSubscription` class."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugSubscription, self).setUp()
        self.bug = self.factory.makeBug()
        self.subscriber = self.factory.makePerson()

    def test_subscribers_can_change_bug_notification_level(self):
        # The bug_notification_level of a subscription can be changed by
        # the subscription's owner.
        with person_logged_in(self.subscriber):
            subscription = self.bug.subscribe(
                self.subscriber, self.subscriber)
            for level in BugNotificationLevel.items:
                subscription.bug_notification_level = level
                self.assertEqual(
                    level, subscription.bug_notification_level)

    def test_only_subscribers_can_change_bug_notification_level(self):
        # Only the owner of the subscription can change its
        # bug_notification_level.
        other_person = self.factory.makePerson()
        with person_logged_in(self.subscriber):
            subscription = self.bug.subscribe(
                self.subscriber, self.subscriber)

        def set_bug_notification_level(level):
            subscription.bug_notification_level = level

        with person_logged_in(other_person):
            for level in BugNotificationLevel.items:
                self.assertRaises(
                    Unauthorized, set_bug_notification_level, level)

    def test_team_owner_can_change_bug_notification_level(self):
        # A team owner can change the bug_notification_level of the
        # team's subscriptions.
        team = self.factory.makeTeam()
        with person_logged_in(team.teamowner):
            subscription = self.bug.subscribe(team, team.teamowner)
            for level in BugNotificationLevel.items:
                subscription.bug_notification_level = level
                self.assertEqual(
                    level, subscription.bug_notification_level)

    def test_team_admin_can_change_bug_notification_level(self):
        # A team's administrators can change the bug_notification_level
        # of its subscriptions.
        team = self.factory.makeTeam()
        with person_logged_in(team.teamowner):
            team.addMember(
                self.subscriber, team.teamowner,
                status=TeamMembershipStatus.ADMIN)
        with person_logged_in(self.subscriber):
            subscription = self.bug.subscribe(team, team.teamowner)
            for level in BugNotificationLevel.items:
                subscription.bug_notification_level = level
                self.assertEqual(
                    level, subscription.bug_notification_level)
