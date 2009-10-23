# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import unittest

from zope.component import getUtility

from canonical.launchpad.ftests import logout
from canonical.launchpad.interfaces.account import AccountStatus
from canonical.launchpad.interfaces.authtoken import LoginTokenType
from canonical.launchpad.interfaces.emailaddress import EmailAddressStatus
from canonical.launchpad.interfaces.logintoken import ILoginTokenSet
from lp.testing import TestCaseWithFactory
from canonical.launchpad.testing.pages import (
    get_feedback_messages, setupBrowser)
from canonical.launchpad.webapp import canonical_url
from canonical.testing import DatabaseFunctionalLayer


class TestPasswordReset(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.email = 'foo@example.com'
        self.person = self.factory.makePerson(
            email=self.email, email_address_status=EmailAddressStatus.NEW)
        self.account = self.person.account

    def test_inactive_accounts_are_activated(self):
        # Resetting the password of an account in the NOACCOUNT state will
        # activate it.
        self.assertEquals(self.account.status, AccountStatus.NOACCOUNT)
        token = getUtility(ILoginTokenSet).new(
            self.person, self.email, self.email,
            LoginTokenType.PASSWORDRECOVERY)
        token_url = str(canonical_url(token))
        logout()
        browser = self._completePasswordResetThroughWeb(token_url)
        self.assertEquals(self.account.status, AccountStatus.ACTIVE)
        self.assertEquals(
            self.account.preferredemail.email, 'foo@example.com')

    def _completePasswordResetThroughWeb(self, token_url):
        """Complete the password reset using the given URL.

        Also make sure the password reset was successful.

        Callsites *must* logout() before calling this method.
        """
        browser = setupBrowser()
        browser.open(token_url)
        browser.getControl(name='field.email').value = self.email
        browser.getControl(name='field.password').value = 'test'
        browser.getControl(name='field.password_dupe').value = 'test'
        browser.getControl('Continue').click()
        feedback = get_feedback_messages(browser.contents)
        self.assertIn('Your password has been reset successfully.', feedback)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
