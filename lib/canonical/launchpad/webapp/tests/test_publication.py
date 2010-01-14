# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests publication.py"""

__metaclass__ = type

import sys
import unittest

from contrib.oauth import OAuthRequest, OAuthSignatureMethod_PLAINTEXT

from storm.exceptions import DisconnectionError
from zope.component import getUtility
from zope.error.interfaces import IErrorReportingUtility
from zope.publisher.interfaces import Retry

from canonical.testing import DatabaseFunctionalLayer
from canonical.launchpad.interfaces.oauth import IOAuthConsumerSet
from canonical.launchpad.ftests import ANONYMOUS, login
from lp.testing import TestCase, TestCaseWithFactory
import canonical.launchpad.webapp.adapter as da
from canonical.launchpad.webapp.interfaces import OAuthPermission
from canonical.launchpad.webapp.publication import (
    is_browser, LaunchpadBrowserPublication)
from canonical.launchpad.webapp.servers import (
    LaunchpadTestRequest, WebServicePublication)


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
        dummy_account = self.factory.makeAccount('Personless account')
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
        da.set_request_started()
        try:
            raise DisconnectionError('Fake')
        except DisconnectionError:
            self.assertRaises(
                Retry,
                publication.handleException,
                None, request, sys.exc_info(), True)
        da.clear_request_started()
        next_oops = error_reporting_utility.getLastOopsReport()

        # Ensure the OOPS mentions the correct exception
        self.assertNotEqual(repr(next_oops).find("DisconnectionError"), -1)

        # Ensure the OOPS is correctly marked as informational only.
        self.assertEqual(next_oops.informational, 'True')

        # Ensure that it is different to the last logged OOPS.
        self.assertNotEqual(repr(last_oops), repr(next_oops))

    def test_bug_504291_logs_oops(self):
        # Bug #504291 was that a Store was being left in a disconnected
        # state after a request, causing subsequent requests handled by that
        # thread to fail. We detect this state in endRequest and log an
        # OOPS to help track down the trigger.
        error_reporting_utility = getUtility(IErrorReportingUtility)
        last_oops = error_reporting_utility.getLastOopsReport()

        request = LaunchpadTestRequest()
        publication = WebServicePublication(None)
        da.set_request_started()

        # Disconnect a store
        from canonical.launchpad.database.emailaddress import EmailAddress
        from canonical.launchpad.interfaces.lpstorm import IMasterStore
        from storm.database import STATE_DISCONNECTED, STATE_RECONNECT
        store = IMasterStore(EmailAddress)
        store._connection._state = STATE_DISCONNECTED

        # Invoke the endRequest hook.
        publication.endRequest(request, None)

        next_oops = error_reporting_utility.getLastOopsReport()

        # Ensure that it is different to the last logged OOPS.
        self.assertNotEqual(repr(last_oops), repr(next_oops))

        # Ensure the OOPS mentions the correct exception
        self.assertNotEqual(repr(next_oops).find("Bug #504291"), -1)

        # Ensure the OOPS is correctly marked as informational only.
        self.assertEqual(next_oops.informational, 'True')

        # Ensure the store has been rolled back and in a usable state.
        self.assertEqual(store._connection._state, STATE_RECONNECT)
        store.find(EmailAddress).first()

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


def test_suite():
    suite = unittest.TestLoader().loadTestsFromName(__name__)
    return suite
