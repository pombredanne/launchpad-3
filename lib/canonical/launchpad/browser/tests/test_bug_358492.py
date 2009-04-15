# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from zope.component import getUtility

import transaction

from canonical.launchpad.interfaces.authtoken import (
    IAuthTokenSet, LoginTokenType)
from canonical.launchpad.ftests import login_person, logout
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.testing.pages import setupBrowser
from canonical.launchpad.webapp.dbpolicy import SSODatabasePolicy
from canonical.launchpad.webapp.interfaces import IStoreSelector
from canonical.testing import DatabaseFunctionalLayer


class TestBug358492(TestCaseWithFactory):
    """https://bugs.edge.launchpad.net/launchpad-registry/+bug/358492"""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.person = self.factory.makePerson()
        login_person(self.person)
        self.person_email = self.person.preferredemail.email
        self.person.deactivateAccount('For testing')
        # Need to commit here so that the deactivated person is seen on other
        # stores.
        transaction.commit()

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

    def test_password_is_reset(self):
        getUtility(IStoreSelector).push(SSODatabasePolicy())
        token = getUtility(IAuthTokenSet).new(
            self.person.account, self.person_email, self.person_email,
            LoginTokenType.PASSWORDRECOVERY, redirection_url=None)
        getUtility(IStoreSelector).pop()
        browser = self._finishPasswordReset(
            token, 'http://openid.launchpad.dev')
        self.assertEqual(browser.url, 'http://openid.launchpad.dev')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
