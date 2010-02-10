# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test harness for running the new-login.txt tests."""

__metaclass__ = type

__all__ = []

import httplib
import unittest

import mechanize

from openid.consumer.consumer import FAILURE, SUCCESS

from canonical.launchpad.interfaces.account import AccountStatus
from canonical.launchpad.testing.pages import (
    extract_text, find_main_content, find_tag_by_id, find_tags_by_class)
from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite
from canonical.launchpad.testing.browser import Browser, setUp, tearDown
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


urls_redirected_to = []


class MyHTTPRedirectHandler(mechanize.HTTPRedirectHandler):
    """Custom HTTPRedirectHandler which stores the URLs redirected to."""

    def redirect_request(self, newurl, req, fp, code, msg, headers):
        urls_redirected_to.append(newurl)
        return mechanize.HTTPRedirectHandler.redirect_request(
            self, newurl, req, fp, code, msg, headers)


class MyMechanizeBrowser(mechanize.Browser):
    """Custom Browser which uses MyHTTPRedirectHandler to handle redirects."""
    handler_classes = mechanize.Browser.handler_classes.copy()
    handler_classes['_redirect'] = MyHTTPRedirectHandler


class TestOpenIDReplayAttack(TestCaseWithFactory):
    layer = AppServerLayer

    def test_replay_attacks_do_not_succeed(self):
        browser = Browser(mech_browser=MyMechanizeBrowser())
        browser.open('http://launchpad.dev:8085/+login')
        # On a JS-enabled browser this page would've been auto-submitted
        # (thanks to the onload handler), but here we have to do it manually.
        self.assertIn('body onload', browser.contents)
        browser.getControl('Continue').click()

        self.assertEquals('Login', browser.title)
        browser.getControl(name='field.email').value = 'test@canonical.com'
        browser.getControl(name='field.password').value = 'test'
        browser.getControl('Continue').click()
        login_status = extract_text(
            find_tag_by_id(browser.contents, 'logincontrol'))
        self.assertIn('Sample Person', login_status)

        # Now we look up (in urls_redirected_to) the +openid-callback URL that
        # was used to complete the authentication and open it on a different
        # browser with a fresh set of cookies.
        replay_browser = Browser()
        [callback_url] = [
            url for url in urls_redirected_to if '+openid-callback' in url]
        self.assertIsNot(None, callback_url)
        replay_browser.open(callback_url)
        login_status = extract_text(
            find_tag_by_id(replay_browser.contents, 'logincontrol'))
        self.assertEquals('Log in / Register', login_status)
        error_msg = find_tags_by_class(replay_browser.contents, 'error')[0]
        self.assertEquals('Nonce already used or out of range',
                          extract_text(error_msg))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))
    suite.addTest(LayeredDocFileSuite(
        'login.txt', setUp=setUp, tearDown=tearDown, layer=AppServerLayer))
    return suite
