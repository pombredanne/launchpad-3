# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.browser.tests.registration import (
    finish_registration_through_the_web)
from canonical.launchpad.interfaces.authtoken import (
    IAuthTokenSet, LoginTokenType)
from canonical.launchpad.interfaces.logintoken import ILoginTokenSet
from lp.testing import TestCaseWithFactory
from canonical.launchpad.webapp.dbpolicy import SSODatabasePolicy
from canonical.launchpad.webapp.interfaces import IStoreSelector
from canonical.testing import DatabaseFunctionalLayer


class TestBug353863(TestCaseWithFactory):
    """https://bugs.edge.launchpad.net/launchpad-registry/+bug/353863"""

    layer = DatabaseFunctionalLayer

    def test_redirection_for_personless_account(self):
        # When we can't look up the OpenID request that triggered the
        # registration, personless accounts are redirected back to
        # openid.launchpad.dev once the registration is finished.
        getUtility(IStoreSelector).push(SSODatabasePolicy())
        token = getUtility(IAuthTokenSet).new(
            requester=None, requesteremail=None, email=u'foo.bar@example.com',
            tokentype=LoginTokenType.NEWPERSONLESSACCOUNT,
            redirection_url=None)
        getUtility(IStoreSelector).pop()
        browser = finish_registration_through_the_web(token)

        self.assertEqual(browser.url, 'http://openid.launchpad.dev')

    def test_redirection_for_full_fledged_account(self):
        # Full-fledged accounts are always redirected back to their home page
        # once the registration is finished and no redirection_url was stored
        # in the token.
        token = getUtility(ILoginTokenSet).new(
            requester=None, requesteremail=None, email=u'foo.bar@example.com',
            tokentype=LoginTokenType.NEWACCOUNT, redirection_url=None)
        browser = finish_registration_through_the_web(token)

        self.assertEqual(browser.url, 'http://launchpad.dev/~foo-bar')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
