# Copyright 2009 Canonical Ltd.  All rights reserved.

import unittest

from zope.component import getUtility

from canonical.launchpad.browser.tests.registration import (
    finish_registration_through_the_web, start_registration_through_the_web)
from canonical.launchpad.interfaces.authtoken import LoginTokenType
from canonical.launchpad.interfaces.logintoken import ILoginTokenSet
from lp.registry.interfaces.person import IPerson
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.testing.pages import get_feedback_messages
from canonical.testing import DatabaseFunctionalLayer


class TestEmailsOfPersonlessAccountsCantBeUsedToRegister(TestCaseWithFactory):
    # If a user tries to create a LP account using an email address that
    # is already associated with a personless account, we'll just tell them
    # they should use their SSO credentials to login.
    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.email = u'testX@example.com'
        self.expected_error = (
            "The email address testX@example.com belongs to an existing "
            "Launchpad Login Service (used by the Ubuntu shop and other "
            "OpenID sites) account, so you can just use that account's "
            "credentials to log into Launchpad.")
        self.personless_account = self.factory.makeAccount(
            'Test account', email=self.email)

    def test_first_step(self):
        # The +login page will prevent users from attempting to register a new
        # account using an email address associated with an existing
        # SSO (personless) account and instead tell them to use the SSO
        # account's credentials to login.
        browser = start_registration_through_the_web(self.email)
        errors = get_feedback_messages(browser.contents)
        self.assertIn(self.expected_error, errors)

    def test_last_step(self):
        # Just like the +login page, the +newaccount page of a LoginToken will
        # render an error if the email address stored on the token is
        # associated with an existing SSO account.
        self.assertIs(IPerson(self.personless_account, None), None)
        # Need to manually create the token here because the check on the
        # +login page (shown by the test above) prevents us from creating it
        # using the web UI.
        self.token = getUtility(ILoginTokenSet).new(
            requester=None, requesteremail=None, email=self.email,
            tokentype=LoginTokenType.NEWACCOUNT, redirection_url=None)
        browser = finish_registration_through_the_web(self.token)
        errors = get_feedback_messages(browser.contents)
        self.assertIn(self.expected_error, errors)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
