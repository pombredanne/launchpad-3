# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the BranchSubscrptions model object.."""

from __future__ import with_statement

__metaclass__ = type

import unittest

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory, person_logged_in


class TestBranchSubscriptionCanBeUnsubscribedbyUser(TestCaseWithFactory):
    """Tests for BranchSubscription.canBeUnsubscribedByUser."""

    layer = DatabaseFunctionalLayer

    def test_none(self):
        """None for a user always returns False."""
        subscription = self.factory.makeBranchSubscription()
        self.assertFalse(subscription.canBeUnsubscribedByUser(None))

    def test_self_subscriber(self):
        """The subscriber has permission to unsubscribe."""
        subscription = self.factory.makeBranchSubscription()
        self.assertTrue(
            subscription.canBeUnsubscribedByUser(subscription.person))

    def test_non_subscriber_fails(self):
        """An unrelated person can't unsubscribe a user."""
        subscription = self.factory.makeBranchSubscription()
        editor = self.factory.makePerson()
        self.assertFalse(subscription.canBeUnsubscribedByUser(editor))

    def test_subscribed_by(self):
        """If a user subscribes someone else, the user can unsubscribe."""
        subscribed_by = self.factory.makePerson()
        subscriber = self.factory.makePerson()
        subscription = self.factory.makeBranchSubscription(
            person=subscriber, subscribed_by=subscribed_by)
        self.assertTrue(subscription.canBeUnsubscribedByUser(subscribed_by))

    def test_team_member_can_unsubscribe(self):
        """Any team member can unsubscribe the team from a branch."""
        team = self.factory.makeTeam()
        member = self.factory.makePerson()
        with person_logged_in(team.teamowner):
            team.addMember(member, team.teamowner)
        subscription = self.factory.makeBranchSubscription(
            person=team, subscribed_by=team.teamowner)
        self.assertTrue(subscription.canBeUnsubscribedByUser(member))

    def test_team_subscriber_can_unsubscribe(self):
        """A team can be unsubscribed by the subscriber even if they are not a
        member."""
        team = self.factory.makeTeam()
        subscribed_by = self.factory.makePerson()
        subscription = self.factory.makeBranchSubscription(
            person=team, subscribed_by=subscribed_by)
        self.assertTrue(subscription.canBeUnsubscribedByUser(subscribed_by))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
