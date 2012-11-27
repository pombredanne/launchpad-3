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

    def test_len_to_user(self):
        # The recipient set length is based on the user activity.
        sender = self.factory.makePerson()
        user = self.factory.makePerson(email='him@eg.dom')
        self.assertEqual(
            1, len(ContactViaWebNotificationRecipientSet(sender, user)))
        inactive_user = self.factory.makePerson(
            email_address_status=EmailAddressStatus.NEW)
        self.assertEqual(
            0, len(
                ContactViaWebNotificationRecipientSet(sender, inactive_user)))

    def test_len_to_admins(self):
        # The recipient set length is based on the number of admins.
        sender = self.factory.makePerson()
        team = self.factory.makeTeam()
        self.assertEqual(
            1, len(ContactViaWebNotificationRecipientSet(sender, team)))
        with person_logged_in(team.teamowner):
            team.teamowner.leave(team)
        self.assertEqual(
            0, len(ContactViaWebNotificationRecipientSet(sender, team)))

    def test_len_to_members(self):
        # The recipient set length is based on the number members.
        sender = self.factory.makePerson()
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

    def makeForm(self, email, subject='subject', message='body'):
        return {
                'field.field.from_': email,
                'field.subject': subject,
                'field.message': message,
                'field.actions.send': 'Send',
                }

    def test_anonymous_redirected(self):
        # Anonymous users cannot use the form.
        user = self.factory.makePerson(name='him')
        view = create_initialized_view(user, '+contactuser')
        response = view.request.response
        self.assertEqual(302, response.getStatus())
        self.assertEqual(
            'http://launchpad.dev/~him', response.getHeader('Location'))

    def test_contact_not_possible_reason_to_user(self):
        # The view explains that the user is inactive.
        inactive_user = self.factory.makePerson(
            email_address_status=EmailAddressStatus.NEW)
        user = self.factory.makePerson()
        with person_logged_in(user):
            view = create_initialized_view(inactive_user, '+contactuser')
        self.assertEqual(
            "The user is not active.", view.contact_not_possible_reason)

    def test_contact_not_possible_reason_to_admins(self):
        # The view explains that the team has no admins.
        team = self.factory.makeTeam()
        with person_logged_in(team.teamowner):
            team.teamowner.leave(team)
        user = self.factory.makePerson()
        with person_logged_in(user):
            view = create_initialized_view(team, '+contactuser')
        self.assertEqual(
            "The team has no admins. Contact the team owner instead.",
            view.contact_not_possible_reason)

    def test_contact_not_possible_reason_to_members(self):
        # The view explains the team has no members..
        team = self.factory.makeTeam()
        with person_logged_in(team.teamowner):
            team.teamowner.leave(team)
        with person_logged_in(team.teamowner):
            view = create_initialized_view(team, '+contactuser')
        self.assertEqual(
            "The team has no members.", view.contact_not_possible_reason)

    def test_missing_subject_and_message(self):
        # The subject and message fields are required.
        sender = self.factory.makePerson(email='me@eg.dom')
        user = self.factory.makePerson()
        form = self.makeForm('me@eg.dom', ' ', ' ')
        with person_logged_in(sender):
            view = create_initialized_view(user, '+contactuser', form=form)
        self.assertEqual(
            [u'You must provide a subject and a message.'], view.errors)
