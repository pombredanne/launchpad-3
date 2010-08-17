# Copyright 2009 Canonical Ltd.  All rights reserved.
from __future__ import with_statement

# pylint: disable-msg=W0105
"""Test harness for running the new-login.txt tests."""

__metaclass__ = type

__all__ = [
    'FakeOpenIDConsumer',
    'FakeOpenIDResponse',
    'IAccountSet_getByOpenIDIdentifier_monkey_patched',
    'SRegResponse_fromSuccessResponse_stubbed',
    'fill_login_form_and_submit',
    ]

from contextlib import contextmanager
from datetime import datetime, timedelta
import httplib
import unittest

import mechanize

from openid.consumer.consumer import FAILURE, SUCCESS
from openid.extensions import sreg

from zope.component import getUtility
from zope.security.management import newInteraction
from zope.security.proxy import removeSecurityProxy
from zope.session.interfaces import ISession

from canonical.launchpad.interfaces.account import AccountStatus, IAccountSet
from canonical.launchpad.testing.pages import (
    extract_text, find_main_content, find_tag_by_id, find_tags_by_class)
from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite
from canonical.launchpad.testing.browser import Browser, setUp, tearDown
from canonical.launchpad.webapp.dbpolicy import MasterDatabasePolicy
from canonical.launchpad.webapp.login import OpenIDCallbackView, OpenIDLogin
from canonical.launchpad.webapp.interfaces import IStoreSelector
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import (
    AppServerLayer, DatabaseFunctionalLayer, FunctionalLayer)

from lp.registry.interfaces.person import IPerson
from lp.testopenid.interfaces.server import ITestOpenIDPersistentIdentity
from lp.testing import logout, TestCaseWithFactory


class FakeOpenIDResponse:

    def __init__(self, identity_url, status=SUCCESS, message='', email=None,
                 full_name=None):
        self.message = message
        self.status = status
        self.identity_url = identity_url
        self.sreg_email = email
        self.sreg_fullname = full_name


class StubbedOpenIDCallbackView(OpenIDCallbackView):
    login_called = False

    def login(self, account):
        super(StubbedOpenIDCallbackView, self).login(account)
        self.login_called = True
        current_policy = getUtility(IStoreSelector).get_current()
        if not isinstance(current_policy, MasterDatabasePolicy):
            raise AssertionError(
                "Not using the master store: %s" % current_policy)


class FakeConsumer:
    """An OpenID consumer that stashes away arguments for test instection."""

    def complete(self, params, requested_url):
        self.params = params
        self.requested_url = requested_url


class FakeConsumerOpenIDCallbackView(OpenIDCallbackView):
    """An OpenID handler with fake consumer so arguments can be inspected."""

    def _getConsumer(self):
        self.fake_consumer = FakeConsumer()
        return self.fake_consumer


@contextmanager
def SRegResponse_fromSuccessResponse_stubbed():
    def sregFromFakeSuccessResponse(cls, success_response, signed_only=True):
        return {'email': success_response.sreg_email,
                'fullname': success_response.sreg_fullname}

    orig_method = sreg.SRegResponse.fromSuccessResponse
    # Use a stub SRegResponse.fromSuccessResponse that works with
    # FakeOpenIDResponses instead of real ones.
    sreg.SRegResponse.fromSuccessResponse = classmethod(
        sregFromFakeSuccessResponse)

    yield

    sreg.SRegResponse.fromSuccessResponse = orig_method


@contextmanager
def IAccountSet_getByOpenIDIdentifier_monkey_patched():
    # Monkey patch getUtility(IAccountSet).getByOpenIDIdentifier() with a
    # method that will raise an AssertionError when it's called and the
    # installed DB policy is not MasterDatabasePolicy.  This is to ensure that
    # the code we're testing forces the use of the master DB by installing the
    # MasterDatabasePolicy.
    account_set = removeSecurityProxy(getUtility(IAccountSet))
    orig_getByOpenIDIdentifier = account_set.getByOpenIDIdentifier

    def fake_getByOpenIDIdentifier(identifier):
        current_policy = getUtility(IStoreSelector).get_current()
        if not isinstance(current_policy, MasterDatabasePolicy):
            raise AssertionError(
                "Not using the master store: %s" % current_policy)
        return orig_getByOpenIDIdentifier(identifier)

    account_set.getByOpenIDIdentifier = fake_getByOpenIDIdentifier

    yield

    account_set.getByOpenIDIdentifier = orig_getByOpenIDIdentifier


class TestOpenIDCallbackView(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def _createViewWithResponse(
            self, account, response_status=SUCCESS, response_msg='',
            view_class=StubbedOpenIDCallbackView):
        openid_response = FakeOpenIDResponse(
            ITestOpenIDPersistentIdentity(account).openid_identity_url,
            status=response_status, message=response_msg,
            email='non-existent@example.com', full_name='Foo User')
        return self._createAndRenderView(
            openid_response, view_class=view_class)

    def _createAndRenderView(self, response,
                             view_class=StubbedOpenIDCallbackView):
        request = LaunchpadTestRequest(
            form={'starting_url': 'http://launchpad.dev/after-login'},
            environ={'PATH_INFO': '/'})
        # The layer we use sets up an interaction (by calling login()), but we
        # want to use our own request in the interaction, so we logout() and
        # setup a newInteraction() using our request.
        logout()
        newInteraction(request)
        view = view_class(object(), request)
        view.initialize()
        view.openid_response = response
        # Monkey-patch getByOpenIDIdentifier() to make sure the view uses the
        # master DB. This mimics the problem we're trying to avoid, where
        # getByOpenIDIdentifier() doesn't find a newly created account because
        # it looks in the slave database.
        with IAccountSet_getByOpenIDIdentifier_monkey_patched():
            html = view.render()
        return view, html

    def test_full_fledged_account(self):
        # In the common case we just login and redirect to the URL specified
        # in the 'starting_url' query arg.
        person = self.factory.makePerson()
        with SRegResponse_fromSuccessResponse_stubbed():
            view, html = self._createViewWithResponse(person.account)
        self.assertTrue(view.login_called)
        response = view.request.response
        self.assertEquals(httplib.TEMPORARY_REDIRECT, response.getStatus())
        self.assertEquals(view.request.form['starting_url'],
                          response.getHeader('Location'))
        # The 'last_write' flag was not updated (unlike in the other test
        # methods) because in this case we didn't have to create a
        # Person/Account entry, so it's ok for further requests to hit the
        # slave DBs.
        self.assertNotIn('last_write', ISession(view.request)['lp.dbpolicy'])

    def test_gather_params(self):
        # If the currently requested URL includes a query string, the
        # parameters in the query string must be included when constructing
        # the params mapping (which is then used to complete the open ID
        # response).  OpenIDCallbackView._gather_params does that gathering.
        request = LaunchpadTestRequest(
            SERVER_URL='http://example.com',
            QUERY_STRING='foo=bar',
            form={'starting_url': 'http://launchpad.dev/after-login'},
            environ={'PATH_INFO': '/'})
        view = OpenIDCallbackView(context=None, request=None)
        params = view._gather_params(request)
        expected_params = {
            'starting_url': 'http://launchpad.dev/after-login',
            'foo': 'bar',
        }
        self.assertEquals(params, expected_params)

    def test_gather_params_with_unicode_data(self):
        # If the currently requested URL includes a query string, the
        # parameters in the query string will be included when constructing
        # the params mapping (which is then used to complete the open ID
        # response) and if there are non-ASCII characters in the query string,
        # they are properly decoded.
        request = LaunchpadTestRequest(
            SERVER_URL='http://example.com',
            QUERY_STRING='foo=%E1%9B%9D',
            environ={'PATH_INFO': '/'})
        view = OpenIDCallbackView(context=None, request=None)
        params = view._gather_params(request)
        self.assertEquals(params['foo'], u'\u16dd')

    def test_unexpected_multivalue_fields(self):
        # The parameter gatering doesn't expect to find multi-valued form
        # field and it reports an error if it finds any.
        request = LaunchpadTestRequest(
            SERVER_URL='http://example.com',
            QUERY_STRING='foo=1&foo=2',
            environ={'PATH_INFO': '/'})
        view = OpenIDCallbackView(context=None, request=None)
        self.assertRaises(ValueError, view._gather_params, request)

    def test_csrfmiddlewaretoken_is_ignored(self):
        # Show that the _gather_params filters out the errant
        # csrfmiddlewaretoken form field.  See comment in _gather_params for
        # more info.
        request = LaunchpadTestRequest(
            SERVER_URL='http://example.com',
            QUERY_STRING='foo=bar',
            form={'starting_url': 'http://launchpad.dev/after-login',
                'csrfmiddlewaretoken': '12345'},
            environ={'PATH_INFO': '/'})
        view = OpenIDCallbackView(context=None, request=None)
        params = view._gather_params(request)
        expected_params = {
            'starting_url': 'http://launchpad.dev/after-login',
            'foo': 'bar',
        }
        self.assertEquals(params, expected_params)

    def test_get_requested_url(self):
        # The OpenIDCallbackView needs to pass the currently-being-requested
        # URL to the OpenID library.  OpenIDCallbackView._get_requested_url
        # returns the URL.
        request = LaunchpadTestRequest(
            SERVER_URL='http://example.com',
            QUERY_STRING='foo=bar',
            form={'starting_url': 'http://launchpad.dev/after-login'})
        view = OpenIDCallbackView(context=None, request=None)
        url = view._get_requested_url(request)
        self.assertEquals(url, 'http://example.com?foo=bar')

    def test_open_id_callback_handles_query_string(self):
        # If the currently requested URL includes a query string, the
        # parameters in the query string must be included when constructing
        # the params mapping (which is then used to complete the open ID
        # response).
        request = LaunchpadTestRequest(
            SERVER_URL='http://example.com',
            QUERY_STRING='foo=bar',
            form={'starting_url': 'http://launchpad.dev/after-login'},
            environ={'PATH_INFO': '/'})
        view = FakeConsumerOpenIDCallbackView(object(), request)
        view.initialize()
        self.assertEquals(
            view.fake_consumer.params,
            {
                'starting_url': 'http://launchpad.dev/after-login',
                'foo': 'bar',
            })
        self.assertEquals(
            view.fake_consumer.requested_url,'http://example.com?foo=bar')

    def test_personless_account(self):
        # When there is no Person record associated with the account, we
        # create one.
        account = self.factory.makeAccount('Test account')
        self.assertIs(None, IPerson(account, None))
        with SRegResponse_fromSuccessResponse_stubbed():
            view, html = self._createViewWithResponse(account)
        self.assertIsNot(None, IPerson(account, None))
        self.assertTrue(view.login_called)
        response = view.request.response
        self.assertEquals(httplib.TEMPORARY_REDIRECT, response.getStatus())
        self.assertEquals(view.request.form['starting_url'],
                          response.getHeader('Location'))

        # We also update the last_write flag in the session, to make sure
        # further requests use the master DB and thus see the newly created
        # stuff.
        self.assertLastWriteIsSet(view.request)

    def test_unseen_identity(self):
        # When we get a positive assertion about an identity URL we've never
        # seen, we automatically register an account with that identity
        # because someone who registered on login.lp.net or login.u.c should
        # be able to login here without any further steps.
        identifier = '4w7kmzU'
        account_set = getUtility(IAccountSet)
        self.assertRaises(
            LookupError, account_set.getByOpenIDIdentifier, identifier)
        openid_response = FakeOpenIDResponse(
            'http://testopenid.dev/+id/%s' % identifier, status=SUCCESS,
            email='non-existent@example.com', full_name='Foo User')
        with SRegResponse_fromSuccessResponse_stubbed():
            view, html = self._createAndRenderView(openid_response)
        self.assertTrue(view.login_called)
        account = account_set.getByOpenIDIdentifier(identifier)
        self.assertIsNot(None, account)
        self.assertEquals(AccountStatus.ACTIVE, account.status)
        self.assertEquals('non-existent@example.com',
                          removeSecurityProxy(account.preferredemail).email)
        person = IPerson(account, None)
        self.assertIsNot(None, person)
        self.assertEquals('Foo User', person.displayname)

        # We also update the last_write flag in the session, to make sure
        # further requests use the master DB and thus see the newly created
        # stuff.
        self.assertLastWriteIsSet(view.request)

    def test_unseen_identity_with_registered_email(self):
        # When we get a positive assertion about an identity URL we've never
        # seen but whose email address is already registered, we just change
        # the identity URL that's associated with the existing email address.
        identifier = '4w7kmzU'
        email = 'test@example.com'
        account = self.factory.makeAccount(
            'Test account', email=email, status=AccountStatus.DEACTIVATED)
        account_set = getUtility(IAccountSet)
        self.assertRaises(
            LookupError, account_set.getByOpenIDIdentifier, identifier)
        openid_response = FakeOpenIDResponse(
            'http://testopenid.dev/+id/%s' % identifier, status=SUCCESS,
            email=email, full_name='Foo User')
        with SRegResponse_fromSuccessResponse_stubbed():
            view, html = self._createAndRenderView(openid_response)
        self.assertTrue(view.login_called)

        # The existing account's openid_identifier was updated, the account
        # was reactivated and its preferred email was set, but its display
        # name was not changed.
        self.assertEquals(identifier, account.openid_identifier)
        self.assertEquals(AccountStatus.ACTIVE, account.status)
        self.assertEquals(
            email, removeSecurityProxy(account.preferredemail).email)
        person = IPerson(account, None)
        self.assertIsNot(None, person)
        self.assertEquals('Test account', person.displayname)

        # We also update the last_write flag in the session, to make sure
        # further requests use the master DB and thus see the newly created
        # stuff.
        self.assertLastWriteIsSet(view.request)

    def test_deactivated_account(self):
        # The user has the account's password and is trying to login, so we'll
        # just re-activate their account.
        email = 'foo@example.com'
        account = self.factory.makeAccount(
            'Test account', email=email, status=AccountStatus.DEACTIVATED)
        self.assertIs(None, IPerson(account, None))
        openid_identifier = removeSecurityProxy(account).openid_identifier
        openid_response = FakeOpenIDResponse(
            'http://testopenid.dev/+id/%s' % openid_identifier,
            status=SUCCESS, email=email, full_name=account.displayname)
        with SRegResponse_fromSuccessResponse_stubbed():
            view, html = self._createAndRenderView(openid_response)
        self.assertIsNot(None, IPerson(account, None))
        self.assertTrue(view.login_called)
        response = view.request.response
        self.assertEquals(httplib.TEMPORARY_REDIRECT, response.getStatus())
        self.assertEquals(view.request.form['starting_url'],
                          response.getHeader('Location'))
        self.assertEquals(AccountStatus.ACTIVE, account.status)
        self.assertEquals(email, account.preferredemail.email)
        # We also update the last_write flag in the session, to make sure
        # further requests use the master DB and thus see the newly created
        # stuff.
        self.assertLastWriteIsSet(view.request)

    def test_never_used_account(self):
        # The account was created by one of our scripts but was never
        # activated, so we just activate it.
        email = 'foo@example.com'
        account = self.factory.makeAccount(
            'Test account', email=email, status=AccountStatus.NOACCOUNT)
        self.assertIs(None, IPerson(account, None))
        openid_identifier = removeSecurityProxy(account).openid_identifier
        openid_response = FakeOpenIDResponse(
            'http://testopenid.dev/+id/%s' % openid_identifier,
            status=SUCCESS, email=email, full_name=account.displayname)
        with SRegResponse_fromSuccessResponse_stubbed():
            view, html = self._createAndRenderView(openid_response)
        self.assertIsNot(None, IPerson(account, None))
        self.assertTrue(view.login_called)
        self.assertEquals(AccountStatus.ACTIVE, account.status)
        self.assertEquals(email, account.preferredemail.email)
        # We also update the last_write flag in the session, to make sure
        # further requests use the master DB and thus see the newly created
        # stuff.
        self.assertLastWriteIsSet(view.request)

    def test_suspended_account(self):
        # There's a chance that our OpenID Provider lets a suspended account
        # login, but we must not allow that.
        account = self.factory.makeAccount(
            'Test account', status=AccountStatus.SUSPENDED)
        with SRegResponse_fromSuccessResponse_stubbed():
            view, html = self._createViewWithResponse(account)
        self.assertFalse(view.login_called)
        main_content = extract_text(find_main_content(html))
        self.assertIn('This account has been suspended', main_content)

    def test_negative_openid_assertion(self):
        # The OpenID provider responded with a negative assertion, so the
        # login error page is shown.
        account = self.factory.makeAccount('Test account')
        view, html = self._createViewWithResponse(
            account, response_status=FAILURE,
            response_msg='Server denied check_authentication')
        self.assertFalse(view.login_called)
        main_content = extract_text(find_main_content(html))
        self.assertIn('Your login was unsuccessful', main_content)

    def test_negative_openid_assertion_when_user_already_logged_in(self):
        # The OpenID provider responded with a negative assertion, but the
        # user already has a valid cookie, so we add a notification message to
        # the response and redirect to the starting_url specified in the
        # OpenID response.
        test_account = self.factory.makeAccount('Test account')

        class StubbedOpenIDCallbackViewLoggedIn(StubbedOpenIDCallbackView):
            account = test_account

        view, html = self._createViewWithResponse(
            test_account, response_status=FAILURE,
            response_msg='Server denied check_authentication',
            view_class=StubbedOpenIDCallbackViewLoggedIn)
        self.assertFalse(view.login_called)
        response = view.request.response
        self.assertEquals(httplib.TEMPORARY_REDIRECT, response.getStatus())
        self.assertEquals(view.request.form['starting_url'],
                          response.getHeader('Location'))
        notification_msg = view.request.response.notifications[0].message
        expected_msg = ('Your authentication failed but you were already '
                        'logged into Launchpad')
        self.assertIn(expected_msg, notification_msg)

    def test_IAccountSet_getByOpenIDIdentifier_monkey_patched(self):
        with IAccountSet_getByOpenIDIdentifier_monkey_patched():
            self.assertRaises(
                AssertionError,
                getUtility(IAccountSet).getByOpenIDIdentifier, 'foo')

    def assertLastWriteIsSet(self, request):
        last_write = ISession(request)['lp.dbpolicy']['last_write']
        self.assertTrue(datetime.utcnow() - last_write < timedelta(minutes=1))


class TestOpenIDCallbackRedirects(TestCaseWithFactory):
    layer = FunctionalLayer

    APPLICATION_URL = 'http://example.com'
    STARTING_URL = APPLICATION_URL + '/start'

    def test_open_id_callback_redirect_from_get(self):
        # If OpenID callback request was a GET, the starting_url is extracted
        # correctly.
        view = OpenIDCallbackView(context=None, request=None)
        view.request = LaunchpadTestRequest(
            SERVER_URL=self.APPLICATION_URL,
            form={'starting_url': self.STARTING_URL})
        view._redirect()
        self.assertEquals(
            httplib.TEMPORARY_REDIRECT, view.request.response.getStatus())
        self.assertEquals(
            view.request.response.getHeader('Location'), self.STARTING_URL)

    def test_open_id_callback_redirect_from_post(self):
        # If OpenID callback request was a POST, the starting_url is extracted
        # correctly.
        view = OpenIDCallbackView(context=None, request=None)
        view.request = LaunchpadTestRequest(
            SERVER_URL=self.APPLICATION_URL, form={'fake': 'value'},
            QUERY_STRING='starting_url='+self.STARTING_URL)
        view._redirect()
        self.assertEquals(
            httplib.TEMPORARY_REDIRECT, view.request.response.getStatus())
        self.assertEquals(
            view.request.response.getHeader('Location'), self.STARTING_URL)

    def test_openid_callback_redirect_fallback(self):
        # If OpenID callback request was a POST or GET with no form or query
        # string values at all, then the application URL is used.
        view = OpenIDCallbackView(context=None, request=None)
        view.request = LaunchpadTestRequest(SERVER_URL=self.APPLICATION_URL)
        view._redirect()
        self.assertEquals(
            httplib.TEMPORARY_REDIRECT, view.request.response.getStatus())
        self.assertEquals(
            view.request.response.getHeader('Location'), self.APPLICATION_URL)


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


def fill_login_form_and_submit(browser, email_address, password):
    assert browser.getControl(name='field.email') is not None, (
        "We don't seem to be looking at a login form.")
    browser.getControl(name='field.email').value = email_address
    browser.getControl(name='field.password').value = password
    browser.getControl('Continue').click()


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
        fill_login_form_and_submit(browser, 'test@canonical.com', 'test')
        login_status = extract_text(
            find_tag_by_id(browser.contents, 'logincontrol'))
        self.assertIn('name12', login_status)

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


class FakeOpenIDRequest:
    extensions = None
    return_to = None

    def addExtension(self, extension):
        if self.extensions is None:
            self.extensions = [extension]
        else:
            self.extensions.append(extension)

    def shouldSendRedirect(self):
        return False

    def htmlMarkup(self, trust_root, return_to):
        self.return_to = return_to
        return None


class FakeOpenIDConsumer:

    def begin(self, url):
        return FakeOpenIDRequest()


class StubbedOpenIDLogin(OpenIDLogin):

    def _getConsumer(self):
        return FakeOpenIDConsumer()


class TestOpenIDLogin(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_return_to_with_non_ascii_chars(self):
        # Sometimes the +login link will have non-ascii characters in the
        # query string, and we need to include those in the return_to URL that
        # we pass to the OpenID provider, so we must utf-encode them.
        request = LaunchpadTestRequest(
            form={'non_ascii_field': 'subproc\xc3\xa9s'})
        # This is a hack to make the request.getURL(1) call issued by the view
        # not raise an IndexError.
        request._app_names = ['foo']
        view = StubbedOpenIDLogin(object(), request)
        view()
        self.assertIn(
            'non_ascii_field%3Dsubproc%C3%A9s', view.openid_request.return_to)

    def test_sreg_fields(self):
        # We request the user's email address and Full Name (through the SREG
        # extension) to the OpenID provider so that we can automatically
        # register unseen OpenID identities.
        request = LaunchpadTestRequest()
        # This is a hack to make the request.getURL(1) call issued by the view
        # not raise an IndexError.
        request._app_names = ['foo']
        view = StubbedOpenIDLogin(object(), request)
        view()
        extensions = view.openid_request.extensions
        self.assertIsNot(None, extensions)
        sreg_extension = extensions[0]
        self.assertIsInstance(sreg_extension, sreg.SRegRequest)
        self.assertEquals(['email', 'fullname'],
                          sorted(sreg_extension.allRequestedFields()))


class TestOpenIDRealm(TestCaseWithFactory):
    # The realm (aka trust_root) specified by the RP is "designed to give the
    # end user an indication of the scope of the authentication request", so
    # for us the realm will always be the root URL of the mainsite.
    layer = AppServerLayer

    def test_realm_for_mainsite(self):
        browser = Browser()
        browser.open('http://launchpad.dev:8085/+login')
        # At this point browser.contents contains a hidden form which would've
        # been auto-submitted if we had in-browser JS support, but since we
        # don't we can easily inspect what's in the form.
        self.assertEquals('http://launchpad.dev:8085/',
                          browser.getControl(name='openid.realm').value)

    def test_realm_for_vhosts(self):
        browser = Browser()
        browser.open('http://bugs.launchpad.dev:8085/+login')
        # At this point browser.contents contains a hidden form which would've
        # been auto-submitted if we had in-browser JS support, but since we
        # don't we can easily inspect what's in the form.
        self.assertEquals('http://launchpad.dev:8085/',
                          browser.getControl(name='openid.realm').value)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))
    suite.addTest(LayeredDocFileSuite(
        'login.txt', setUp=setUp, tearDown=tearDown, layer=AppServerLayer))
    return suite
