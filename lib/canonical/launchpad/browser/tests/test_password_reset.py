# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import unittest

from zope.component import getUtility

import transaction
from canonical.launchpad.browser.logintoken import ResetPasswordView
from canonical.launchpad.ftests import LaunchpadFormHarness
from canonical.launchpad.interfaces.account import AccountStatus
from canonical.launchpad.interfaces.authtoken import LoginTokenType
from canonical.launchpad.interfaces.emailaddress import EmailAddressStatus
from canonical.launchpad.interfaces.logintoken import ILoginTokenSet
from lp.testing import TestCaseWithFactory
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
        self._completePasswordReset(token)
        self.assertEquals(self.account.status, AccountStatus.ACTIVE)
        self.assertEquals(
            self.account.preferredemail.email, 'foo@example.com')

    def _completePasswordReset(self, token):
        harness = LaunchpadFormHarness(token, ResetPasswordView)
        form = {'field.email': self.email,
                'field.password': 'test',
                'field.password_dupe': 'test'}
        harness.submit('continue', form)
        self.assertFalse(harness.hasErrors())
        # Need to manually commit because we're interested in testing the
        # changes done by the view on the token's requester (i.e.
        # self.person).
        transaction.commit()


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
