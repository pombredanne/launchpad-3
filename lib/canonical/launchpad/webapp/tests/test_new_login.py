# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test harness for running the new-login.txt tests."""

__metaclass__ = type

__all__ = []

import httplib
import unittest

from openid.consumer.consumer import FAILURE, SUCCESS

from canonical.launchpad.interfaces.account import AccountStatus
from canonical.launchpad.testing.pages import extract_text, find_main_content
from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite
from canonical.launchpad.testing.browser import setUp, tearDown
from canonical.launchpad.webapp.login import OpenIDCallbackView
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import AppServerLayer, DatabaseFunctionalLayer

from lp.registry.interfaces.person import IPerson
from lp.testopenid.interfaces.server import ITestOpenIDPersistentIdentity
from lp.testing import TestCaseWithFactory


class FakeOpenIDResponse:

    def __init__(self, identity_url, status=SUCCESS, message=''):
        self.message = message
        self.status = status
        self.identity_url = identity_url


class StubbedOpenIDCallbackView(OpenIDCallbackView):
    openid_response = None
    login_called = False

    def login(self, account):
        self.login_called = True


class TestOpenIDCallbackView(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def _createView(self, account, response_status=SUCCESS, response_msg=''):
        request = LaunchpadTestRequest(
            form={'starting_url': 'http://launchpad.dev/after-login'},
            environ={'PATH_INFO': '/'})
        view = StubbedOpenIDCallbackView(object(), request)
        view.openid_response = FakeOpenIDResponse(
            ITestOpenIDPersistentIdentity(account).openid_identity_url,
            status=response_status, message=response_msg)
        return view

    def test_full_fledged_account(self):
        # In the common case we just login and redirect to the URL specified
        # in the 'starting_url' query arg.
        person = self.factory.makePerson()
        view = self._createView(person.account)
        view()
        self.assertTrue(view.login_called)
        response = view.request.response
        self.assertEquals(httplib.TEMPORARY_REDIRECT, response.getStatus())
        self.assertEquals(view.request.form['starting_url'],
                          response.getHeader('Location'))

    def test_personless_account(self):
        # When there is no Person record associated with the account, we
        # create one.
        account = self.factory.makeAccount('Test account')
        self.assertIs(None, IPerson(account, None))
        view = self._createView(account)
        view()
        self.assertIsNot(None, IPerson(account, None))
        self.assertTrue(view.login_called)
        response = view.request.response
        self.assertEquals(httplib.TEMPORARY_REDIRECT, response.getStatus())
        self.assertEquals(view.request.form['starting_url'],
                          response.getHeader('Location'))

    def test_deactivated_account(self):
        # The user has the account's password and is trying to login, so we'll
        # just re-activate their account.
        account = self.factory.makeAccount(
            'Test account', status=AccountStatus.DEACTIVATED)
        self.assertIs(None, IPerson(account, None))
        view = self._createView(account)
        view()
        self.assertIsNot(None, IPerson(account, None))
        self.assertTrue(view.login_called)
        response = view.request.response
        self.assertEquals(httplib.TEMPORARY_REDIRECT, response.getStatus())
        self.assertEquals(view.request.form['starting_url'],
                          response.getHeader('Location'))

    def test_suspended_account(self):
        # There's a chance that our OpenID Provider lets a suspended account
        # login, but we must not allow that.
        account = self.factory.makeAccount(
            'Test account', status=AccountStatus.SUSPENDED)
        view = self._createView(account)
        html = view()
        self.assertFalse(view.login_called)
        main_content = extract_text(find_main_content(html))
        self.assertIn('This account has been suspended', main_content)

    def test_negative_openid_assertion(self):
        # The OpenID provider responded with a negative assertion, so the
        # login error page is shown.
        account = self.factory.makeAccount('Test account')
        view = self._createView(
            account, response_status=FAILURE,
            response_msg='Server denied check_authentication')
        html = view()
        self.assertFalse(view.login_called)
        main_content = extract_text(find_main_content(html))
        self.assertIn('Your login was unsuccessful', main_content)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))
    suite.addTest(LayeredDocFileSuite(
        'new-login.txt', setUp=setUp, tearDown=tearDown,
        layer=AppServerLayer))
    return suite
