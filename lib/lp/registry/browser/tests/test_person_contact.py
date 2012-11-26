# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Test views and helpers related to the contact person feature."""

__metaclass__ = type

from lp.registry.browser.person import ContactViaWebNotificationRecipientSet
from lp.services.identity.interfaces.emailaddress import EmailAddressStatus
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.views import create_initialized_view


class ContactViaWebNotificationRecipientSetTestCase(TestCaseWithFactory):
    """Tests the behaviour of ContactViaWebNotificationRecipientSet."""

    layer = DatabaseFunctionalLayer

    def test_len(self):
        # The recipient set length is based on the number or recipient
        # found by the selection rules.
        sender = self.factory.makePerson(email='me@eg.dom')
        # Contact user.
        user = self.factory.makePerson(email='him@eg.dom')
        self.assertEqual(
            1, len(ContactViaWebNotificationRecipientSet(sender, user)))
        # Contact team admins.
        team = self.factory.makeTeam()
        self.assertEqual(
            1, len(ContactViaWebNotificationRecipientSet(sender, team)))
        with person_logged_in(team.teamowner):
            team.teamowner.leave(team)
        self.assertEqual(
            0, len(ContactViaWebNotificationRecipientSet(sender, team)))
        # Contact team members.
        sender_team = self.factory.makeTeam(members=[sender])
        owner = sender_team.teamowner
        self.assertEqual(
            2, len(ContactViaWebNotificationRecipientSet(owner, sender_team)))
        with person_logged_in(owner):
            owner.leave(sender_team)
        self.assertEqual(
            1, len(ContactViaWebNotificationRecipientSet(owner, sender_team)))


class EmailToPersonViewTestCase(TestCaseWithFactory):
    """Tests the behaviour of EmailToPersonView."""

    layer = DatabaseFunctionalLayer

    def test_contact_not_possible_reason(self):
        sender = self.factory.makePerson(email='me@eg.dom')
        # Contact inactive user.
        user = self.factory.makePerson(
            email_address_status=EmailAddressStatus.NEW)
        with person_logged_in(sender):
            view = create_initialized_view(user, '+contactuser')
        self.assertEqual(
            "The user is not active.", view.contact_not_possible_reason)
        # Contact team without admins.
        team = self.factory.makeTeam()
        with person_logged_in(team.teamowner):
            team.teamowner.leave(team)
        with person_logged_in(sender):
            view = create_initialized_view(team, '+contactuser')
        self.assertEqual(
            "The team has no admins. Contact the team owner instead.",
            view.contact_not_possible_reason)
        # Contact team without members.
        with person_logged_in(team.teamowner):
            view = create_initialized_view(team, '+contactuser')
        self.assertEqual(
            "The team has no members.", view.contact_not_possible_reason)
