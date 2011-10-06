# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for the private MailingList API."""

__metaclass__ = type
__all__ = []


import transaction

from canonical.config import config
from canonical.launchpad.interfaces.emailaddress import EmailAddressStatus
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.tests.mailinglists_helper import new_team
from lp.registry.xmlrpc.mailinglist import (
    BYUSER,
    ENABLED,
    MailingListAPIView,
    )
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


class MailingListAPITestCase(TestCaseWithFactory):
    """Tests for MailingListAPIView."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Create a team with a list and subscribe self.member to it."""
        super(MailingListAPITestCase, self).setUp()
        self.team, self.mailing_list = new_team('team-a', with_list=True)
        self.member = self.factory.makePersonByName('Bob')
        with person_logged_in(self.member):
            self.member.join(self.team)
        self.mailing_list.subscribe(self.member)
        self.api = MailingListAPIView(None, None)

    def _assertMembership(self, expected):
        """Assert that the named team has exactly the expected membership."""
        transaction.commit()
        all_info = self.api.getMembershipInformation([self.team.name])
        team_info = all_info.get(self.team.name)
        self.failIf(team_info is None)
        team_info.sort()
        expected.sort()
        self.assertEqual(team_info, expected)

    def test_getMembershipInformation_with_hidden_email(self):
        """Verify that hidden email addresses are still reported correctly."""
        with person_logged_in(self.member):
            self.member.hide_email_addresses = True
        # API runs without a logged in user.
        self._assertMembership([
            ('archive@mail-archive.dev', '', 0, ENABLED),
            ('bob.person@example.com', 'Bob Person', 0, ENABLED),
            ('bperson@example.org', u'Bob Person', 0, BYUSER),
            ('no-priv@canonical.com', u'No Privileges Person', 0, BYUSER),
            ])

    def test_isRegisteredInLaunchpad_person_with_preferred_email(self):
        self.factory.makePerson(email='me@fndor.dom')
        self.assertTrue(self.api.isRegisteredInLaunchpad('me@fndor.dom'))

    def test_isRegisteredInLaunchpad_email_without_preferred_email(self):
        self.factory.makePerson(
            email='me@fndor.dom', email_address_status=EmailAddressStatus.NEW)
        self.assertFalse(self.api.isRegisteredInLaunchpad('me@fndor.dom'))

    def test_isRegisteredInLaunchpad_email_no_email_address(self):
        self.assertFalse(self.api.isRegisteredInLaunchpad('me@fndor.dom'))

    def test_isRegisteredInLaunchpad_email_without_person(self):
        self.factory.makeAccount('Me', email='me@fndor.dom')
        self.assertFalse(self.api.isRegisteredInLaunchpad('me@fndor.dom'))

    def test_isRegisteredInLaunchpad_archive_address_is_false(self):
        # The Mailman archive address can never be owned by an Lp user
        # because such a user would have acces to all lists.
        email = config.mailman.archive_address
        self.factory.makePerson(email=email)
        self.assertFalse(self.api.isRegisteredInLaunchpad(email))

    def test_isRegisteredInLaunchpad_team(self):
        self.factory.makeTeam(email='me@fndor.dom')
        self.assertFalse(self.api.isRegisteredInLaunchpad('me@fndor.dom'))
