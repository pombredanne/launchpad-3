# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.interfaces.authtoken import (
    IAuthTokenSet, LoginTokenType)
from canonical.launchpad.interfaces.logintoken import ILoginTokenSet
from canonical.launchpad.ftests import login_person, logout
from lp.testing import TestCaseWithFactory
from canonical.launchpad.testing.pages import setupBrowser
from canonical.launchpad.webapp.dbpolicy import SSODatabasePolicy
from canonical.launchpad.webapp.interfaces import IStoreSelector
from canonical.testing import DatabaseFunctionalLayer


class TestBug358498(TestCaseWithFactory):
    """https://bugs.edge.launchpad.net/launchpad-registry/+bug/358498"""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.account = self.factory.makeAccount('Test account')
        login_person(self.account)
        self.account_email = self.account.preferredemail.email

        self.person = self.factory.makePerson(name='test-person')
        login_person(self.person)
        self.person_email = self.person.preferredemail.email

    def _finishPasswordReset(self, token, root_url):
        """Create a Browser and drive it through resetting the password.

        Return the Browser object after the password is reset.
        """
        logout()
        browser = setupBrowser()
        browser.open(root_url + '/token/' + token.token)
        browser.getControl(name='field.email').value = token.email
        browser.getControl(name='field.password').value = 'test'
        browser.getControl(name='field.password_dupe').value = 'test'
        browser.getControl('Continue').click()
        return browser

    def test_redirection_for_personless_account(self):
        # When we can't look up the OpenID request that triggered the
        # password reset, personless accounts are redirected back to
        # openid.launchpad.dev once the password is reset.
        getUtility(IStoreSelector).push(SSODatabasePolicy())
        token = getUtility(IAuthTokenSet).new(
            self.account, self.account_email, self.account_email,
            LoginTokenType.PASSWORDRECOVERY, redirection_url=None)
        getUtility(IStoreSelector).pop()
        browser = self._finishPasswordReset(
            token, 'http://openid.launchpad.dev')

        self.assertEqual(browser.url, 'http://openid.launchpad.dev')

    def test_redirection_for_full_fledged_account(self):
        # Full-fledged accounts are always redirected back to Launchpad's
        # front page once the password is reset and no redirection_url was
        # stored in the token.
        token = getUtility(ILoginTokenSet).new(
            self.person, self.person_email, self.person_email,
            LoginTokenType.PASSWORDRECOVERY, redirection_url=None)
        browser = self._finishPasswordReset(token, 'http://launchpad.dev')

        self.assertEqual(browser.url, 'http://launchpad.dev')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
