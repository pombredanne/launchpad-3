# Copyright 2009 Canonical Ltd.  All rights reserved.
"""Tests publication.py"""

__metaclass__ = type


import unittest

from contrib.oauth import OAuthRequest, OAuthSignatureMethod_PLAINTEXT

from zope.component import getUtility

from canonical.testing import DatabaseFunctionalLayer
from canonical.launchpad.interfaces.oauth import IOAuthConsumerSet
from canonical.launchpad.ftests import ANONYMOUS, login
from lp.testing import TestCaseWithFactory
from canonical.launchpad.webapp.interfaces import OAuthPermission
from canonical.launchpad.webapp.servers import (
    LaunchpadTestRequest, WebServicePublication)


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


def test_suite():
    suite = unittest.TestLoader().loadTestsFromName(__name__)
    return suite
