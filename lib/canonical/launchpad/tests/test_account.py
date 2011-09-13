# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from canonical.launchpad.ftests import (
    ANONYMOUS,
    login,
    )
from canonical.launchpad.webapp.authorization import check_permission
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory


class TestAccount(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_account_repr_ansii(self):
        # Verify that ANSI displayname is ascii safe.
        distro = self.factory.makeAccount(u'\xdc-account')
        ignore, displayname, status_1, status_2 = repr(distro).rsplit(' ', 3)
        self.assertEqual("'\\xdc-account'", displayname)
        self.assertEqual('(Active account)>', '%s %s' % (status_1, status_2))

    def test_account_repr_unicode(self):
        # Verify that Unicode displayname is ascii safe.
        distro = self.factory.makeAccount(u'\u0170-account')
        ignore, displayname, status_1, status_2 = repr(distro).rsplit(' ', 3)
        self.assertEqual("'\\u0170-account'", displayname)


class TestPersonlessAccountPermissions(TestCaseWithFactory):
    """In order for Person-less accounts to see their non-public details and
    email addresses, we had to change the security adapters for IAccount and
    IEmailAddress to accept the 'user' argument being either a Person or an
    Account.

    Here we login() with one of these person-less accounts and show that they
    can see their details, including email addresses.
    """
    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self, 'no-priv@canonical.com')
        self.email = 'test@example.com'
        self.account = self.factory.makeAccount(
            'Test account, without a person', email=self.email)

    def test_can_view_their_emails(self):
        login(self.email)
        self.failUnless(
            check_permission('launchpad.View', self.account.preferredemail))

    def test_can_view_their_own_details(self):
        login(self.email)
        self.failUnless(check_permission('launchpad.View', self.account))

    def test_can_change_their_own_details(self):
        login(self.email)
        self.failUnless(check_permission('launchpad.Edit', self.account))

    def test_emails_of_personless_acounts_cannot_be_seen_by_others(self):
        # Email addresses are visible to others only when the user has
        # explicitly chosen to have them shown, and that state is stored in
        # IPerson.hide_email_addresses, so for accounts that have no
        # associated Person, we will hide the email addresses from others.
        login('no-priv@canonical.com')
        self.failIf(check_permission(
            'launchpad.View', self.account.preferredemail))

        # Anonymous users can't see them either.
        login(ANONYMOUS)
        self.failIf(check_permission(
            'launchpad.View', self.account.preferredemail))
