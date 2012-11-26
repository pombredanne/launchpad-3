# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Test views and helpers related to the contact person feature."""

__metaclass__ = type

from lp.registry.browser.person import ContactViaWebNotificationRecipientSet
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.views import create_initialized_view


class ContactViaWebNotificationRecipientSetTestCase(TestCaseWithFactory):
    """Tests for the public OpenID identifier shown on the profile page."""

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
        self.assertEqual(
            1, len(ContactViaWebNotificationRecipientSet(sender, sender_team)))
        with person_logged_in(sender_team.teamowner):
            sender_team.teamowner.leave(sender_team)
        self.assertEqual(
            0, len(ContactViaWebNotificationRecipientSet(sender, sender_team)))
