# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = []


import unittest

from canonical.launchpad.ftests import login
from canonical.testing import LaunchpadFunctionalLayer

from lp.registry.interfaces.mailinglistsubscription import (
    MailingListAutoSubscribePolicy)
from lp.registry.interfaces.person import TeamSubscriptionPolicy
from lp.testing import TestCaseWithFactory


class MailingList_getSubscribers_TestCase(TestCaseWithFactory):
    """Tests for `IMailingList`.getSubscribers()."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        # Create a team (tied to a mailing list) with one former member, one
        # pending member and one active member.
        TestCaseWithFactory.setUp(self)
        login('foo.bar@canonical.com')
        former_member = self.factory.makePerson()
        pending_member = self.factory.makePerson()
        active_member = self.active_member = self.factory.makePerson()
        self.team, self.mailing_list = self.factory.makeTeamAndMailingList(
            'test-mailinglist', 'team-owner')
        self.team.subscriptionpolicy = TeamSubscriptionPolicy.MODERATED

        # Each of our members want to be subscribed to a team's mailing list
        # whenever they join the team.
        former_member.mailing_list_auto_subscribe_policy = (
            MailingListAutoSubscribePolicy.ALWAYS)
        active_member.mailing_list_auto_subscribe_policy = (
            MailingListAutoSubscribePolicy.ALWAYS)
        pending_member.mailing_list_auto_subscribe_policy = (
            MailingListAutoSubscribePolicy.ALWAYS)

        pending_member.join(self.team)
        self.assertEqual(False, pending_member.inTeam(self.team))

        self.team.addMember(former_member, reviewer=self.team.teamowner)
        former_member.leave(self.team)
        self.assertEqual(False, former_member.inTeam(self.team))

        self.team.addMember(active_member, reviewer=self.team.teamowner)
        self.assertEqual(True, active_member.inTeam(self.team))

    def test_only_active_members_can_be_subscribers(self):
        # Even though our 3 members want to subscribe to the team's mailing
        # list, only the active member is considered a subscriber.
        subscribers = [self.active_member]
        self.assertEqual(
            subscribers, list(self.mailing_list.getSubscribers()))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
