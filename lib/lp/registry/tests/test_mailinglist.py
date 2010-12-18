# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = []

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.mailinglistsubscription import (
    MailingListAutoSubscribePolicy,
    )
from lp.registry.interfaces.person import TeamSubscriptionPolicy
from lp.testing import login_celebrity, person_logged_in, TestCaseWithFactory


class MailingList_getSubscribers_TestCase(TestCaseWithFactory):
    """Tests for `IMailingList`.getSubscribers()."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.team, self.mailing_list = self.factory.makeTeamAndMailingList(
            'test-mailinglist', 'team-owner')

    def test_only_active_members_can_be_subscribers(self):
        former_member = self.factory.makePerson()
        pending_member = self.factory.makePerson()
        active_member = self.active_member = self.factory.makePerson()
        # Each of our members want to be subscribed to a team's mailing list
        # whenever they join the team.
        login_celebrity('admin')
        former_member.mailing_list_auto_subscribe_policy = (
            MailingListAutoSubscribePolicy.ALWAYS)
        active_member.mailing_list_auto_subscribe_policy = (
            MailingListAutoSubscribePolicy.ALWAYS)
        pending_member.mailing_list_auto_subscribe_policy = (
            MailingListAutoSubscribePolicy.ALWAYS)
        self.team.subscriptionpolicy = TeamSubscriptionPolicy.MODERATED
        pending_member.join(self.team)
        self.team.addMember(former_member, reviewer=self.team.teamowner)
        former_member.leave(self.team)
        self.team.addMember(active_member, reviewer=self.team.teamowner)
        # Even though our 3 members want to subscribe to the team's mailing
        # list, only the active member is considered a subscriber.
        self.assertEqual(
            [active_member], list(self.mailing_list.getSubscribers()))

    def test_getSubscribers_order(self):
        person_1 = self.factory.makePerson(name="pb1", displayname="Me")
        with person_logged_in(person_1):
            person_1.mailing_list_auto_subscribe_policy = (
                MailingListAutoSubscribePolicy.ALWAYS)
            person_1.join(self.team)
        person_2 = self.factory.makePerson(name="pa2", displayname="Me")
        with person_logged_in(person_2):
            person_2.mailing_list_auto_subscribe_policy = (
                MailingListAutoSubscribePolicy.ALWAYS)
            person_2.join(self.team)
        subscribers = self.mailing_list.getSubscribers()
        self.assertEqual(2, subscribers.count())
        self.assertEqual(
            ['pa2', 'pb1'], [person.name for person in subscribers])
