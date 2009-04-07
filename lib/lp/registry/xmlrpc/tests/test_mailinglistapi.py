# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for the private MailingList API."""

__metaclass__ = type
__all__ = []


import unittest

from canonical.launchpad.ftests import login, login_person, ANONYMOUS, logout
from lp.registry.tests.mailinglists_helper import new_team
from canonical.launchpad.testing.factory import LaunchpadObjectFactory
from canonical.launchpad.xmlrpc.mailinglist import (
    MailingListAPIView, BYUSER, ENABLED)
from canonical.testing import LaunchpadFunctionalLayer


class MailingListAPITestCase(unittest.TestCase):
    """Tests for MailingListAPIView."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        """Create a team with a list and subscribe self.member to it."""
        login('foo.bar@canonical.com')
        self.team, self.mailing_list = new_team('team-a', with_list=True)
        self.member = LaunchpadObjectFactory().makePersonByName('Bob')
        self.member.join(self.team)
        self.mailing_list.subscribe(self.member)
        self.api = MailingListAPIView(None, None)

    def tearDown(self):
        logout()

    def _assertMembership(self, expected):
        """Assert that the named team has exactly the expected membership."""
        all_info = self.api.getMembershipInformation([self.team.name])
        team_info = all_info.get(self.team.name)
        self.failIf(team_info is None)
        team_info.sort()
        expected.sort()
        self.assertEqual(team_info, expected)

    def test_getMembershipInformation_with_hidden_email(self):
        """Verify that hidden email addresses are still reported correctly."""
        login_person(self.member)
        self.member.hide_email_addresses = True
        # API runs without a logged in user.
        login(ANONYMOUS)
        self._assertMembership([
            ('archive@mail-archive.dev', '', 0, ENABLED),
            ('bob.person@example.com', 'Bob Person', 0, ENABLED),
            ('bperson@example.org', u'Bob Person', 0, BYUSER),
            ('no-priv@canonical.com', u'No Privileges Person', 0, BYUSER),
            ])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
