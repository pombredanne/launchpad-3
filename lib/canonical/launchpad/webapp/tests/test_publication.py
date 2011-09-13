# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests publication.py"""

__metaclass__ = type

import logging
import sys

from contrib.oauth import (
    OAuthRequest,
    OAuthSignatureMethod_PLAINTEXT,
    )
from storm.database import (
    STATE_DISCONNECTED,
    STATE_RECONNECT,
    )
from storm.exceptions import DisconnectionError
from storm.zope.interfaces import IZStorm
from zope.component import getUtility
from zope.error.interfaces import IErrorReportingUtility
from zope.interface import directlyProvides
from zope.publisher.interfaces import (
    NotFound,
    Retry,
    )

from canonical.config import dbconfig
from canonical.launchpad.database.emailaddress import EmailAddress
from canonical.launchpad.ftests import (
    ANONYMOUS,
    login,
    )
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.launchpad.interfaces.oauth import (
    IOAuthConsumerSet,
    IOAuthSignedRequest,
    )
from canonical.launchpad.readonly import is_read_only
from canonical.launchpad.tests.readonly import (
    remove_read_only_file,
    touch_read_only_file,
    )
import canonical.launchpad.webapp.adapter as dbadapter
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector,
    MAIN_STORE,
    MASTER_FLAVOR,
    NoReferrerError,
    OAuthPermission,
    OffsiteFormPostError,
    SLAVE_FLAVOR,
    )
from canonical.launchpad.webapp.publication import (
    is_browser,
    LaunchpadBrowserPublication,
    maybe_block_offsite_form_post,
    OFFSITE_POST_WHITELIST,
    )
from canonical.launchpad.webapp.servers import (
    LaunchpadTestRequest,
    WebServicePublication,
    )
from canonical.launchpad.webapp.vhosts import allvhosts
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    FunctionalLayer,
    )
from lp.testing import (
    TestCase,
    TestCaseWithFactory,
    )


class TestLaunchpadBrowserPublication(TestCase):

    def test_callTraversalHooks_appends_to_traversed_objects(self):
        # Traversed objects are appended to request.traversed_objects in the
        # order they're traversed.
        obj1 = object()
        obj2 = object()
        request = LaunchpadTestRequest()
        publication = LaunchpadBrowserPublication(None)
        publication.callTraversalHooks(request, obj1)
        publication.callTraversalHooks(request, obj2)
        self.assertEquals(request.traversed_objects, [obj1, obj2])

    def test_callTraversalHooks_appends_only_once_to_traversed_objects(self):
        # callTraversalHooks() may be called more than once for a given
        # traversed object, but if that's the case we won't add the same
        # object twice to traversed_objects.
        obj1 = obj2 = object()
        request = LaunchpadTestRequest()
        publication = LaunchpadBrowserPublication(None)
        publication.callTraversalHooks(request, obj1)
        publication.callTraversalHooks(request, obj2)
        self.assertEquals(request.traversed_objects, [obj1])


class TestReadOnlyModeSwitches(TestCase):
    # At the beginning of every request (in publication.beforeTraversal()), we
    # check to see if we've changed from/to read-only/read-write and if there
    # was a change we remove the main_master/slave stores from ZStorm, forcing
    # them to be recreated the next time they're needed, thus causing them to
    # point to the correct databases.
    layer = DatabaseFunctionalLayer

    def tearDown(self):
        TestCase.tearDown(self)
        # If a DB policy was installed (e.g. by publication.beforeTraversal),
        # uninstall it.
        try:
            getUtility(IStoreSelector).pop()
        except IndexError:
            pass
        # Cleanup needed so that further tests can start processing other
        # requests (e.g. calling beforeTraversal).
        self.publication.endRequest(self.request, None)
        # Force pending mode switches to actually happen and get logged so
        # that we don't interfere with other tests.
        assert not is_read_only(), (
            "A test failed to clean things up properly, leaving the app "
            "in read-only mode.")

    def setUp(self):
        TestCase.setUp(self)
        # Get the main_master/slave stores just to make sure they're added to
        # ZStorm.
        master = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        slave = getUtility(IStoreSelector).get(MAIN_STORE, SLAVE_FLAVOR)
        self.master_connection = master._connection
        self.slave_connection = slave._connection
        self.zstorm = getUtility(IZStorm)
        self.publication = LaunchpadBrowserPublication(None)
        # Run through once to initialize. beforeTraversal will never
        # disconnect Stores the first run through because there is no
        # need.
        request = LaunchpadTestRequest()
        self.publication.beforeTraversal(request)
        self.publication.endRequest(request, None)
        getUtility(IStoreSelector).pop()

        self.request = LaunchpadTestRequest()

    @property
    def zstorm_stores(self):
        return [name for (name, store) in self.zstorm.iterstores()]

    def test_no_mode_changes(self):
        # Make sure the master/slave stores are present in zstorm.
        self.assertIn('launchpad-main-master', self.zstorm_stores)
        self.assertIn('launchpad-main-slave', self.zstorm_stores)

        self.publication.beforeTraversal(self.request)

        # Since the mode didn't change, the stores were left in zstorm.
        self.assertIn('launchpad-main-master', self.zstorm_stores)
        self.assertIn('launchpad-main-slave', self.zstorm_stores)

        # With the store's connection being the same as before.
        master = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        self.assertIs(self.master_connection, master._connection)

        # And they still point to the read-write databases.
        self.assertEquals(
            dbconfig.rw_main_master.strip(),
            # XXX: 2009-01-12, salgado, bug=506536: We shouldn't need to go
            # through private attributes to get to the store's database.
            master._connection._database.dsn_without_user.strip())

    def test_changing_modes(self):
        # Make sure the master/slave stores are present in zstorm.
        self.assertIn('launchpad-main-master', self.zstorm_stores)
        self.assertIn('launchpad-main-slave', self.zstorm_stores)

        try:
            touch_read_only_file()
            self.publication.beforeTraversal(self.request)
        finally:
            # Tell remove_read_only_file() to not assert that the mode switch
            # actually happened, as we know it won't happen until this request
            # is finished.
            remove_read_only_file(assert_mode_switch=False)

        # Here the mode has changed to read-only, so the stores were removed
        # from zstorm.
        self.assertNotIn('launchpad-main-master', self.zstorm_stores)
        self.assertNotIn('launchpad-main-slave', self.zstorm_stores)

        # If they're needed again, they'll be re-created by ZStorm, and when
        # that happens they will point to the read-only databases.
        master = getUtility(IStoreSelector).get(MAIN_STORE, SLAVE_FLAVOR)
        self.assertEquals(
            dbconfig.ro_main_master.strip(),
            # XXX: 2009-01-12, salgado, bug=506536: We shouldn't need to go
            # through private attributes to get to the store's database.
            master._connection._database.dsn_without_user.strip())


class TestReadOnlyNotifications(TestCase):
    """Tests for `LaunchpadBrowserPublication.maybeNotifyReadOnlyMode`."""

    layer = FunctionalLayer

    def setUp(self):
        TestCase.setUp(self)
        touch_read_only_file()
        self.addCleanup(remove_read_only_file, assert_mode_switch=False)

    def test_notification(self):
        # In read-only mode, maybeNotifyReadOnlyMode adds a warning that
        # changes cannot be made to every request that supports notifications.
        publication = LaunchpadBrowserPublication(None)
        request = LaunchpadTestRequest()
        publication.maybeNotifyReadOnlyMode(request)
        self.assertEqual(1, len(request.notifications))
        notification = request.notifications[0]
        self.assertEqual(logging.WARNING, notification.level)
        self.assertTrue('read-only mode' in notification.message)

    def test_notification_xmlrpc(self):
        # Even in read-only mode, maybeNotifyReadOnlyMode doesn't try to add a
        # notification to a request that doesn't support notifications.
        from canonical.launchpad.webapp.servers import PublicXMLRPCRequest
        publication = LaunchpadBrowserPublication(None)
        request = PublicXMLRPCRequest(None, {})
        # This is just assertNotRaises
        publication.maybeNotifyReadOnlyMode(request)


class TestWebServicePublication(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        login(ANONYMOUS)

    def _getRequestForPersonAndAccountWithDifferentIDs(self):
        """Return a LaunchpadTestRequest with the correct OAuth parameters in
        its form.
        """
        # Create a lone account followed by an account-with-person just to
        # make sure in the second one the ID of the account and the person are
        # different.
        self.factory.makeAccount('Personless account')
        person = self.factory.makePerson()
        self.failIfEqual(person.id, person.account.id)

        # Create an access token for our new person.
        consumer = getUtility(IOAuthConsumerSet).new('test-consumer')
        request_token = consumer.newRequestToken()
        request_token.review(
            person, permission=OAuthPermission.READ_PUBLIC, context=None)
        access_token = request_token.createAccessToken()

        # Use oauth.OAuthRequest just to generate a dictionary containing all
        # the parameters we need to use in a valid OAuth request, using the
        # access token we just created for our new person.
        oauth_request = OAuthRequest.from_consumer_and_token(
            consumer, access_token)
        oauth_request.sign_request(
            OAuthSignatureMethod_PLAINTEXT(), consumer, access_token)
        return LaunchpadTestRequest(form=oauth_request.parameters)

    def test_getPrincipal_for_person_and_account_with_different_ids(self):
        # WebServicePublication.getPrincipal() does not rely on accounts
        # having the same IDs as their associated person entries to work.
        request = self._getRequestForPersonAndAccountWithDifferentIDs()
        principal = WebServicePublication(None).getPrincipal(request)
        self.failIf(principal is None)

    def test_disconnect_logs_oops(self):
        error_reporting_utility = getUtility(IErrorReportingUtility)
        last_oops = error_reporting_utility.getLastOopsReport()

        # Ensure that OOPS reports are generated for database
        # disconnections, as per Bug #373837.
        request = LaunchpadTestRequest()
        publication = WebServicePublication(None)
        dbadapter.set_request_started()
        try:
            raise DisconnectionError('Fake')
        except DisconnectionError:
            self.assertRaises(
                Retry,
                publication.handleException,
                None, request, sys.exc_info(), True)
        dbadapter.clear_request_started()
        next_oops = error_reporting_utility.getLastOopsReport()

        # Ensure the OOPS mentions the correct exception
        self.assertTrue(repr(next_oops).find("DisconnectionError") != -1,
            "next_oops was %r" % next_oops)

        # Ensure that it is different to the last logged OOPS.
        self.assertNotEqual(repr(last_oops), repr(next_oops))

    def test_store_disconnected_after_request_handled_logs_oops(self):
        # Bug #504291 was that a Store was being left in a disconnected
        # state after a request, causing subsequent requests handled by that
        # thread to fail. We detect this state in endRequest and log an
        # OOPS to help track down the trigger.
        error_reporting_utility = getUtility(IErrorReportingUtility)
        last_oops = error_reporting_utility.getLastOopsReport()

        request = LaunchpadTestRequest()
        publication = WebServicePublication(None)
        dbadapter.set_request_started()

        # Disconnect a store
        store = IMasterStore(EmailAddress)
        store._connection._state = STATE_DISCONNECTED

        # Invoke the endRequest hook.
        publication.endRequest(request, None)

        next_oops = error_reporting_utility.getLastOopsReport()

        # Ensure that it is different to the last logged OOPS.
        self.assertNotEqual(repr(last_oops), repr(next_oops))

        # Ensure the OOPS mentions the correct exception
        self.assertNotEqual(repr(next_oops).find("Bug #504291"), -1)

        # Ensure the store has been rolled back and in a usable state.
        self.assertEqual(store._connection._state, STATE_RECONNECT)
        store.find(EmailAddress).first()  # Confirms Store is working.

    def test_is_browser(self):
        # No User-Agent: header.
        request = LaunchpadTestRequest()
        self.assertFalse(is_browser(request))

        # Browser User-Agent: header.
        request = LaunchpadTestRequest(environ={
            'USER_AGENT': 'Mozilla/42 Extreme Edition'})
        self.assertTrue(is_browser(request))

        # Robot User-Agent: header.
        request = LaunchpadTestRequest(environ={'USER_AGENT': 'BottyBot'})
        self.assertFalse(is_browser(request))


class TestBlockingOffsitePosts(TestCase):
    """We are very particular about what form POSTs we will accept."""

    def test_NoReferrerError(self):
        # If this request is a POST and there is no referrer, an exception is
        # raised.
        request = LaunchpadTestRequest(
            method='POST', environ=dict(PATH_INFO='/'))
        self.assertRaises(
            NoReferrerError, maybe_block_offsite_form_post, request)

    def test_nonPOST_requests(self):
        # If the request isn't a POST it is always allowed.
        request = LaunchpadTestRequest(method='SOMETHING')
        maybe_block_offsite_form_post(request)

    def test_localhost_is_ok(self):
        # we accept "localhost" and "localhost:9000" as valid referrers.  See
        # comments in the code as to why and for a related bug report.
        request = LaunchpadTestRequest(
            method='POST', environ=dict(PATH_INFO='/', REFERER='localhost'))
        # this doesn't raise an exception
        maybe_block_offsite_form_post(request)

    def test_whitelisted_paths(self):
        # There are a few whitelisted POST targets that don't require the
        # referrer be LP.  See comments in the code as to why and for related
        # bug reports.
        for path in OFFSITE_POST_WHITELIST:
            request = LaunchpadTestRequest(
                method='POST', environ=dict(PATH_INFO=path))
            # this call shouldn't raise an exception
            maybe_block_offsite_form_post(request)

    def test_OAuth_signed_requests(self):
        # Requests that are OAuth signed are allowed.
        request = LaunchpadTestRequest(
            method='POST', environ=dict(PATH_INFO='/'))
        directlyProvides(request, IOAuthSignedRequest)
        # this call shouldn't raise an exception
        maybe_block_offsite_form_post(request)

    def test_nonbrowser_requests(self):
        # Requests that are from non-browsers are allowed.
        class FakeNonBrowserRequest:
            method = 'SOMETHING'

        # this call shouldn't raise an exception
        maybe_block_offsite_form_post(FakeNonBrowserRequest)

    def test_onsite_posts(self):
        # Other than the explicit execptions, all POSTs have to come from a
        # known LP virtual host.
        for hostname in allvhosts.hostnames:
            referer = 'http://' + hostname + '/foo'
            request = LaunchpadTestRequest(
                method='POST', environ=dict(PATH_INFO='/', REFERER=referer))
            # this call shouldn't raise an exception
            maybe_block_offsite_form_post(request)

    def test_offsite_posts(self):
        # If a post comes from an unknown host an execption is raised.
        disallowed_hosts = ['example.com', 'not-subdomain.launchpad.net']
        for hostname in disallowed_hosts:
            referer = 'http://' + hostname + '/foo'
            request = LaunchpadTestRequest(
                method='POST', environ=dict(PATH_INFO='/', REFERER=referer))
            self.assertRaises(
                OffsiteFormPostError, maybe_block_offsite_form_post, request)

    def test_unparsable_referer(self):
        # If a post has a referer that is unparsable as a URI an exception is
        # raised.
        referer = 'this is not a URI'
        request = LaunchpadTestRequest(
            method='POST', environ=dict(PATH_INFO='/', REFERER=referer))
        self.assertRaises(
            OffsiteFormPostError, maybe_block_offsite_form_post, request)

    def test_openid_callback_with_query_string(self):
        # An OpenId provider (OP) may post to the +openid-callback URL with a
        # query string and without a referer.  These posts need to be allowed.
        path_info = u'/+openid-callback?starting_url=...'
        request = LaunchpadTestRequest(
            method='POST', environ=dict(PATH_INFO=path_info))
        # this call shouldn't raise an exception
        maybe_block_offsite_form_post(request)


class TestEncodedReferer(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_not_found(self):
        # No oopses are reported when accessing the referer while rendering
        # the page.
        browser = self.getUserBrowser()
        browser.addHeader('Referer', '/whut\xe7foo')
        self.assertRaises(
            NotFound,
            browser.open,
            'http://launchpad.dev/missing')
        self.assertEqual(0, len(self.oopses))


class TestUnicodePath(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_non_ascii_url(self):
        # No oopses are reported when accessing the URL while rendering the
        # page.
        browser = self.getUserBrowser()
        self.assertRaises(
            NotFound,
            browser.open,
            'http://launchpad.dev/%ED%B4%B5')
        self.assertEqual(0, len(self.oopses))
