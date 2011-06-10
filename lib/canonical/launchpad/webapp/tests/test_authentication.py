# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests authentication.py"""

__metaclass__ = type


import unittest

from zope.app.security.principalregistry import UnauthenticatedPrincipal

from contrib.oauth import OAuthRequest

from canonical.config import config
from canonical.launchpad.ftests import login
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite,
    setUp,
    tearDown,
    )
from canonical.launchpad.webapp.authentication import LaunchpadPrincipal
from canonical.launchpad.webapp.login import logInPrincipal
from canonical.launchpad.webapp.publication import LaunchpadBrowserPublication
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing import TestCaseWithFactory


class TestAuthenticationOfPersonlessAccounts(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.email = 'baz@example.com'
        self.request = LaunchpadTestRequest()
        self.account = self.factory.makeAccount(
            'Personless account', email=self.email)
        self.principal = LaunchpadPrincipal(
            self.account.id, self.account.displayname,
            self.account.displayname, self.account)
        login(self.email)

    def test_navigate_anonymously_on_launchpad_dot_net(self):
        # A user with the credentials of a personless account will browse
        # launchpad.net anonymously.
        logInPrincipal(self.request, self.principal, self.email)
        self.request.response.setCookie(
            config.launchpad_session.cookie, 'xxx')

        publication = LaunchpadBrowserPublication(None)
        principal = publication.getPrincipal(self.request)
        self.failUnless(isinstance(principal, UnauthenticatedPrincipal))


class TestOAuthParsing(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_split_oauth(self):
        # OAuth headers are parsed correctly: see bug 314507.
        # This was really a bug in the underlying contrib/oauth.py module, but
        # it has no standalone test case.
        #
        # Note that the 'realm' parameter is not returned, because it's not
        # included in the OAuth calculations.
        headers = OAuthRequest._split_header(
            'OAuth realm="foo", oauth_consumer_key="justtesting"')
        self.assertEquals(headers,
            {'oauth_consumer_key': 'justtesting'})
        headers = OAuthRequest._split_header(
            'OAuth oauth_consumer_key="justtesting"')
        self.assertEquals(headers,
            {'oauth_consumer_key': 'justtesting'})
        headers = OAuthRequest._split_header(
            'OAuth oauth_consumer_key="justtesting", realm="realm"')
        self.assertEquals(headers,
            {'oauth_consumer_key': 'justtesting'})


def test_suite():
    suite = unittest.TestLoader().loadTestsFromName(__name__)
    suite.addTest(LayeredDocFileSuite(
        'test_launchpad_login_source.txt',
        layer=LaunchpadFunctionalLayer, setUp=setUp, tearDown=tearDown))
    return suite
