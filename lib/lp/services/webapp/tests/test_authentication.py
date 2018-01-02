# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests authentication.py"""

__metaclass__ = type


import unittest

from contrib.oauth import OAuthRequest

from lp.services.webapp.authentication import check_oauth_signature
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.testing import (
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.systemdocs import (
    LayeredDocFileSuite,
    setUp,
    tearDown,
    )


class TestOAuthParsing(TestCase):

    def test_split_oauth(self):
        # OAuth headers are parsed correctly: see bug 314507.
        # This was really a bug in the underlying contrib/oauth.py module, but
        # it has no standalone test case.
        #
        # Note that the 'realm' parameter is not returned, because it's not
        # included in the OAuth calculations.
        headers = OAuthRequest._split_header(
            'OAuth realm="foo", oauth_consumer_key="justtesting"')
        self.assertEqual(headers,
            {'oauth_consumer_key': 'justtesting'})
        headers = OAuthRequest._split_header(
            'OAuth oauth_consumer_key="justtesting"')
        self.assertEqual(headers,
            {'oauth_consumer_key': 'justtesting'})
        headers = OAuthRequest._split_header(
            'OAuth oauth_consumer_key="justtesting", realm="realm"')
        self.assertEqual(headers,
            {'oauth_consumer_key': 'justtesting'})


class TestCheckOAuthSignature(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def makeRequest(self, signature, method='PLAINTEXT'):
        form = {
            'oauth_signature_method': method, 'oauth_signature': signature}
        return LaunchpadTestRequest(form=form)

    def test_valid(self):
        token, secret = self.factory.makeOAuthAccessToken()
        request = self.makeRequest('&%s' % secret)
        self.assertTrue(check_oauth_signature(request, token.consumer, token))

    def test_bad_secret(self):
        token, secret = self.factory.makeOAuthAccessToken()
        request = self.makeRequest('&%slol' % secret)
        self.assertFalse(check_oauth_signature(request, token.consumer, token))
        self.assertEqual(401, request.response.getStatus())

    def test_valid_no_token(self):
        token, _ = self.factory.makeOAuthAccessToken()
        request = self.makeRequest('&')
        self.assertTrue(check_oauth_signature(request, token.consumer, None))

    def test_bad_secret_no_token(self):
        token, _ = self.factory.makeOAuthAccessToken()
        request = self.makeRequest('&lol')
        self.assertFalse(check_oauth_signature(request, token.consumer, None))
        self.assertEqual(401, request.response.getStatus())

    def test_not_plaintext(self):
        token, _ = self.factory.makeOAuthAccessToken()
        request = self.makeRequest('&lol', method='HMAC-SHA1')
        self.assertFalse(check_oauth_signature(request, token.consumer, token))
        self.assertEqual(400, request.response.getStatus())

    def test_bad_signature_format(self):
        token, _ = self.factory.makeOAuthAccessToken()
        request = self.makeRequest('lol')
        self.assertFalse(check_oauth_signature(request, token.consumer, token))
        self.assertEqual(401, request.response.getStatus())


def test_suite():
    suite = unittest.TestLoader().loadTestsFromName(__name__)
    suite.addTest(LayeredDocFileSuite(
        'test_launchpad_login_source.txt',
        layer=LaunchpadFunctionalLayer, setUp=setUp, tearDown=tearDown))
    return suite
