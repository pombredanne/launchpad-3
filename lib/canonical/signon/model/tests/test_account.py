# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for `Account` objects under the SSO policy."""

__metaclass__ = type
__all__ = []

import unittest

from zope.component import getUtility

from canonical.launchpad.interfaces.authtoken import (
    IAuthTokenSet, LoginTokenType)
from canonical.launchpad.webapp.interfaces import IStoreSelector
from canonical.signon.dbpolicy import SSODatabasePolicy
from canonical.launchpad.database.tests.test_account import (
    EmailManagementTests)


class EmailManagementWithSSODatabasePolicyTests(EmailManagementTests):
    """Test email management interfaces for `IAccount` with SSO db policy."""

    def setUp(self):
        # Configure database policy to match single sign on server.
        super(EmailManagementWithSSODatabasePolicyTests, self).setUp()
        getUtility(IStoreSelector).push(SSODatabasePolicy())

    def tearDown(self):
        getUtility(IStoreSelector).pop()
        super(EmailManagementWithSSODatabasePolicyTests, self).tearDown()

    def test_getUnvalidatedEmails(self):
        # Test that unvalidated emails can be retrieved using the
        # SSODatabasePolicy.
        account = self.factory.makeAccount("Test Account")
        token = getUtility(IAuthTokenSet).new(
            account, account.preferredemail.email,
            u"unvalidated-email@example.org", LoginTokenType.VALIDATEEMAIL,
            None)
        self.assertEqual(account.getUnvalidatedEmails(),
                         [u"unvalidated-email@example.org"])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
