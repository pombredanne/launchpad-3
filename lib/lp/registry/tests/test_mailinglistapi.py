# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for the private MailingList API."""

__metaclass__ = type
__all__ = []


from lp.registry.tests.mailinglists_helper import new_team
from lp.registry.interfaces.person import (
    PersonalStanding,
    PersonVisibility,
    )
from lp.registry.xmlrpc.mailinglist import (
    BYUSER,
    ENABLED,
    MailingListAPIView,
    )
from lp.services.config import config
from lp.services.identity.interfaces.emailaddress import EmailAddressStatus
from lp.testing import (
    celebrity_logged_in,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.xmlrpc import faults


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
        self.team_expected = sorted([
            (config.mailman.archive_address, '', 0, ENABLED),
            ('bob.person@example.com', 'Bob Person', 0, ENABLED),
            ('bperson@example.org', u'Bob Person', 0, BYUSER),
            ('no-priv@canonical.com', u'No Privileges Person', 0, BYUSER),
            ])

    def test_getMembershipInformation(self):
        # Requesting a sequence of team names returns a dict:
        # team-name: (address, display name, 0, <ENABLED|BYUSER>)
        # where ENABLED are subscribers, and BYUSER are posters.
        team_b, member_b = self.factory.makeTeamWithMailingListSubscribers(
            'team-b', auto_subscribe=False)
        all_info = self.api.getMembershipInformation(
            [self.team.name, team_b.name])
        self.assertEqual(['team-a', 'team-b'], sorted(all_info.keys()))
        self.assertEqual(self.team_expected, sorted(all_info[self.team.name]))

    def test_getMembershipInformation_with_hidden_email(self):
        """Verify that hidden email addresses are still reported correctly."""
        with person_logged_in(self.member):
            self.member.hide_email_addresses = True
        all_info = self.api.getMembershipInformation([self.team.name])
        self.assertEqual(['team-a'], all_info.keys())
        self.assertEqual(self.team_expected, sorted(all_info[self.team.name]))

    def test_getMembershipInformation_remote_public_archive(self):
        # Private teams do not have config.mailman.archive_address,
        # 'archive@mail-archive.dev', in the list of membership information,
        # but public do.
        subscriber = self.factory.makePerson(email='me@eg.dom')
        team_b = self.factory.makeTeam(
            name='team-b', owner=subscriber,
            visibility=PersonVisibility.PRIVATE)
        with person_logged_in(subscriber):
            mailing_list = self.factory.makeMailingList(team_b, subscriber)
            mailing_list.subscribe(subscriber)
        private_expected = [('me@eg.dom', subscriber.displayname, 0, ENABLED)]
        all_info = self.api.getMembershipInformation(['team-a', 'team-b'])
        self.assertEqual(['team-a', 'team-b'], sorted(all_info.keys()))
        self.assertEqual(self.team_expected, sorted(all_info[self.team.name]))
        self.assertEqual(private_expected, sorted(all_info['team-b']))

    def test_getMembershipInformation_no_team(self):
        # Requesting a non-existant team will have None for the subcribers
        all_info = self.api.getMembershipInformation(['not-team'])
        self.assertEqual(['not-team'], sorted(all_info.keys()))
        self.assertIs(None, all_info['not-team'])

    def test_isRegisteredInLaunchpad_person_with_preferred_email(self):
        self.factory.makePerson(email='me@fndor.dom')
        self.assertTrue(self.api.isRegisteredInLaunchpad('me@fndor.dom'))

    def test_isRegisteredInLaunchpad_email_without_preferred_email(self):
        self.factory.makePerson(
            email='me@fndor.dom', email_address_status=EmailAddressStatus.NEW)
        self.assertFalse(self.api.isRegisteredInLaunchpad('me@fndor.dom'))

    def test_isRegisteredInLaunchpad_email_no_email_address(self):
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

    def test_isTeamPublic(self):
        self.factory.makeTeam(
            name='team-b', visibility=PersonVisibility.PRIVATE)
        self.assertIs(True, self.api.isTeamPublic('team-a'))
        self.assertIs(False, self.api.isTeamPublic('team-b'))

    def test_isTeamPublic_fault(self):
        self.assertIsInstance(
            self.api.isTeamPublic('not-team'), faults.NoSuchPersonWithName)

    def test_inGoodStanding(self):
        self.factory.makePerson(email='no@eg.dom')
        yes_person = self.factory.makePerson(email='yes@eg.dom')
        with celebrity_logged_in('admin'):
            yes_person.personal_standing = PersonalStanding.GOOD
        self.assertIs(True, self.api.inGoodStanding('yes@eg.dom'))
        self.assertIs(False, self.api.inGoodStanding('no@eg.dom'))
