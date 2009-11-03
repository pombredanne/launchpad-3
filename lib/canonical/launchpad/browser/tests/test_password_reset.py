# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

import transaction
from canonical.launchpad.browser.logintoken import ResetPasswordView
from canonical.launchpad.ftests import LaunchpadFormHarness
from canonical.launchpad.interfaces.account import AccountStatus
from canonical.launchpad.interfaces.authtoken import LoginTokenType
from canonical.launchpad.interfaces.emailaddress import EmailAddressStatus
from canonical.launchpad.interfaces.logintoken import ILoginTokenSet
from canonical.launchpad.interfaces.lpstorm import IMasterObject
from lp.testing import TestCaseWithFactory
from canonical.testing import DatabaseFunctionalLayer


class TestPasswordReset(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer
    email = 'foo@example.com'

    def _create_inactive_person(self):
        self.person = self.factory.makePerson(
            email=self.email, email_address_status=EmailAddressStatus.NEW)
        self.account = self.person.account
        self.assertEquals(self.account.status, AccountStatus.NOACCOUNT)

    def test_inactive_accounts_are_activated(self):
        # Resetting the password of an account in the NOACCOUNT state will
        # activate it.
        self._create_inactive_person()
        self._resetPassword(ensure_no_errors=True)
        self.assertEquals(self.account.status, AccountStatus.ACTIVE)
        self.assertEquals(
            self.account.preferredemail.email, 'foo@example.com')

    def _create_deactivated_person(self):
        self.person = self.factory.makePerson(email=self.email)
        removeSecurityProxy(self.person.deactivateAccount('Testing'))
        # Get the account from the master DB to make sure it has the changes
        # we did above.
        self.account = IMasterObject(self.person.account)
        self.assertEquals(self.account.status, AccountStatus.DEACTIVATED)

    def test_deactivated_accounts_are_reactivated(self):
        # Resetting the password of an account in the DEACTIVATED state will
        # reactivate it.
        self._create_deactivated_person()
        self._resetPassword(ensure_no_errors=True)
        self.assertEquals(self.account.status, AccountStatus.ACTIVE)
        self.assertEquals(
            self.account.preferredemail.email, 'foo@example.com')

    def _create_suspended_person(self):
        self.person = self.factory.makePerson(email=self.email)
        # Get the account from the master DB as we're going to change it.
        self.account = IMasterObject(self.person.account)
        removeSecurityProxy(self.account).status = AccountStatus.SUSPENDED
        self.assertEquals(self.account.status, AccountStatus.SUSPENDED)

    def test_suspended_accounts_cannot_reset_password(self):
        # It's not possible to reset the password of a SUSPENDED account.
        self._create_suspended_person()
        harness = self._resetPassword()
        notifications = [notification.message
                         for notification in harness.request.notifications]
        self.assertIn(
            'Your password cannot be reset because your account is suspended',
            '\n'.join(notifications))
        self.assertEquals(self.account.status, AccountStatus.SUSPENDED)

    def _resetPassword(self, ensure_no_errors=False):
        token = getUtility(ILoginTokenSet).new(
            self.person, self.email, self.email,
            LoginTokenType.PASSWORDRECOVERY)
        harness = LaunchpadFormHarness(token, ResetPasswordView)
        form = {'field.email': self.email,
                'field.password': 'test',
                'field.password_dupe': 'test'}
        harness.submit('continue', form)
        if ensure_no_errors:
            self.assertFalse(harness.hasErrors())
        # Need to manually commit because we're interested in testing the
        # changes done by the view on the token's requester (i.e.
        # self.person).
        transaction.commit()
        return harness


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
