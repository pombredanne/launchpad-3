# Copyright 2009 Canonical Ltd.  All rights reserved.

import unittest

from canonical.launchpad.ftests import ANONYMOUS, login
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp.authorization import check_permission
from canonical.testing import LaunchpadFunctionalLayer


class TestPersonlessAccountPermissions(TestCaseWithFactory):
    """In order for Person-less accounts to see their non-public details and
    email addresses, we had to change the security adapters for IAccount and
    IEmailAddress to accept the 'user' argument being either a Person or an
    Account.

    Here we login() with one of these person-less accounts and show that they
    can see their details, including email addresses.
    """
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self, 'no-priv@canonical.com')
        self.account = self.factory.makeAccount(
            'Test account, without a person')
        self.account_email = self.factory.makeEmail(
            'test@example.com', None, self.account)

    def test_can_view_their_emails(self):
        login('test@example.com')
        self.failUnless(
            check_permission('launchpad.View', self.account_email))

    def test_can_view_their_own_details(self):
        login('test@example.com')
        self.failUnless(check_permission('launchpad.View', self.account))

    def test_can_change_their_own_details(self):
        login('test@example.com')
        self.failUnless(check_permission('launchpad.Edit', self.account))

    def test_emails_of_personless_acounts_cannot_be_seen_by_others(self):
        # Email addresses are visible to others only when the user has
        # explicitly chosen to have them shown, and that state is stored in
        # IPerson.hide_email_addresses, so for accounts that have no
        # associated Person, we will hide the email addresses from others.
        login('no-priv@canonical.com')
        self.failIf(check_permission('launchpad.View', self.account_email))

        # Anonymous users can't see them either.
        login(ANONYMOUS)
        self.failIf(check_permission('launchpad.View', self.account_email))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
