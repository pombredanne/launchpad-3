# Copyright 2008 Canonical Ltd.  All rights reserved.
"""Tests authentication.py"""

__metaclass__ = type


import unittest

from zope.app.security.principalregistry import UnauthenticatedPrincipal
from zope.component import getUtility

from canonical.config import config
from canonical.testing import (
    DatabaseFunctionalLayer, LaunchpadFunctionalLayer)
from canonical.launchpad.ftests import login
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp.authentication import OpenIDPrincipal
from canonical.launchpad.webapp.login import logInPrincipal
from canonical.launchpad.webapp.publication import LaunchpadBrowserPublication
from canonical.launchpad.webapp.servers import IdPublication
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)


class TestAuthenticationOfPersonLessAccounts(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.request = LaunchpadTestRequest()
        self.account = self.factory.makeAccount('Personless account')
        self.email = self.factory.makeEmail(
            'baz@example.com', person=None, account=self.account)
        self.principal = OpenIDPrincipal(
            self.account.id, self.account.displayname,
            self.account.displayname, self.account)
        login('baz@example.com')

    def test_navigate_anonymously_on_launchpad_dot_net(self):
        # A user with the credentials of a personless account will browse
        # launchpad.net anonymously.
        logInPrincipal(self.request, self.principal, 'baz@example.com')
        self.request.response.setCookie(
            config.launchpad_session.cookie, 'xxx')

        publication = LaunchpadBrowserPublication(None)
        principal = publication.getPrincipal(self.request)
        self.failUnless(isinstance(principal, UnauthenticatedPrincipal))

    def test_navigate_logged_in_on_login_dot_launchpad_dot_net(self):
        # A user with the credentials of a personless account will browse
        # login.launchpad.net logged in as that account.
        logInPrincipal(self.request, self.principal, 'baz@example.com')
        self.request.response.setCookie(
            config.launchpad_session.cookie, 'xxx')

        publication = IdPublication(None)
        principal = publication.getPrincipal(self.request)
        self.failUnless(isinstance(principal, OpenIDPrincipal))
        self.failUnlessEqual(self.principal.id, principal.id)


def test_suite():
    suite = unittest.TestLoader().loadTestsFromName(__name__)
    suite.addTest(LayeredDocFileSuite(
        'test_launchpad_login_source.txt',
        layer=LaunchpadFunctionalLayer, setUp=setUp, tearDown=tearDown))
    return suite
