# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.interfaces.authtoken import (
    IAuthTokenSet, LoginTokenType)
from canonical.launchpad.interfaces.logintoken import ILoginTokenSet
from canonical.launchpad.ftests import logout
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.testing.pages import setupBrowser
from canonical.launchpad.webapp.dbpolicy import SSODatabasePolicy
from canonical.launchpad.webapp.interfaces import IStoreSelector
from canonical.testing import DatabaseFunctionalLayer


class TestBug353863(TestCaseWithFactory):
    """https://bugs.edge.launchpad.net/launchpad-registry/+bug/353863"""

    layer = DatabaseFunctionalLayer

    def _finishRegistration(self, token, root_url):
        """Create a Browser and drive it through the account registration.

        Return the Browser object after the registration is finished.
        """
        logout()
        browser = setupBrowser()
        browser.open(root_url + '/token/' + token.token)
        browser.getControl('Name').value = 'New User'
        browser.getControl('Create password').value = 'test'
        browser.getControl(name='field.password_dupe').value = 'test'
        browser.getControl('Continue').click()
        return browser

    def test_redirection_for_personless_account(self):
        # When we can't look up the OpenID request that triggered the
        # registration, personless accounts are redirected back to
        # openid.launchpad.dev once the registration is finished.
        getUtility(IStoreSelector).push(SSODatabasePolicy())
        token = getUtility(IAuthTokenSet).new(
            requester=None, requesteremail=None, email=u'foo.bar@example.com',
            tokentype=LoginTokenType.NEWPERSONLESSACCOUNT,
            redirection_url=None)
        getUtility(IStoreSelector).pop()
        browser = self._finishRegistration(
            token, 'http://openid.launchpad.dev')

        self.assertEqual(browser.url, 'http://openid.launchpad.dev')

    def test_redirection_for_full_fledged_account(self):
        # Full-fledged accounts are always redirected back to their home page
        # once the registration is finished and no redirection_url was stored
        # in the token.
        token = getUtility(ILoginTokenSet).new(
            requester=None, requesteremail=None, email=u'foo.bar@example.com',
            tokentype=LoginTokenType.NEWACCOUNT, redirection_url=None)
        browser = self._finishRegistration(token, 'http://launchpad.dev')

        self.assertEqual(browser.url, 'http://launchpad.dev/~foo-bar')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
