# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for AuthToken code."""

__metaclass__ = type

import email
import unittest

from storm.exceptions import LostObjectError
from storm.store import Store
import transaction
from zope.component import getUtility

from canonical.launchpad.interfaces.account import AccountStatus
from canonical.launchpad.interfaces.authtoken import (
    IAuthToken, IAuthTokenSet, LoginTokenType)
from lp.services.mail import stub
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp.dbpolicy import SSODatabasePolicy
from canonical.launchpad.webapp.interfaces import IStoreSelector
from canonical.testing import DatabaseFunctionalLayer


class SSODatabasePolicyTests(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer
    def setUp(self):
        super(SSODatabasePolicyTests, self).setUp()
        getUtility(IStoreSelector).push(SSODatabasePolicy())

    def tearDown(self):
        getUtility(IStoreSelector).pop()
        super(SSODatabasePolicyTests, self).tearDown()


class AuthTokenTests(SSODatabasePolicyTests):

    layer = DatabaseFunctionalLayer

    def test_consume(self):
        account = self.factory.makeAccount(
            u"Test Account", status=AccountStatus.ACTIVE)
        token_type = LoginTokenType.VALIDATEEMAIL

        token1 = getUtility(IAuthTokenSet).new(
            account, u"requester@example.net", u"newemail@example.net",
            token_type, None)
        token2 = getUtility(IAuthTokenSet).new(
            account, u"requester@example.net", u"newemail@example.net",
            token_type, None)
        Store.of(token1).flush()
        self.assertNotEqual(token1, token2)

        token1.consume()
        Store.of(token1).flush()
        self.assertNotEqual(token1.date_consumed, None)

        # Second token has also been consumed.
        self.assertNotEqual(token2.date_consumed, None)

    def test_sendEmailValidationRequest(self):
        account = self.factory.makeAccount(
            u"Test Account", status=AccountStatus.ACTIVE)
        token = getUtility(IAuthTokenSet).new(
            account, u"requester@example.net", u"newemail@example.net",
            LoginTokenType.VALIDATEEMAIL, None)
        token.sendEmailValidationRequest()
        transaction.commit()

        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        msg = email.message_from_string(raw_msg)

        self.assertEqual(to_addrs, ["newemail@example.net"])
        self.assertEqual(
            msg["Subject"], "Login Service: Validate your email address")

    def test_sendPasswordResetEmail(self):
        account = self.factory.makeAccount(
            u"Test Account", status=AccountStatus.ACTIVE)
        token = getUtility(IAuthTokenSet).new(
            account, u"requester@example.net", u"newemail@example.net",
            LoginTokenType.PASSWORDRECOVERY, None)
        token.sendPasswordResetEmail()
        transaction.commit()

        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        msg = email.message_from_string(raw_msg)

        self.assertEqual(to_addrs, ["newemail@example.net"])
        self.assertEqual(
            msg["Subject"], "Login Service: Forgotten Password")

    def test_sendNewUserEmail(self):
        token = getUtility(IAuthTokenSet).new(
            None, u"requester@example.net", u"newemail@example.net",
            LoginTokenType.NEWACCOUNT, None)
        token.sendNewUserEmail()
        transaction.commit()

        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        msg = email.message_from_string(raw_msg)

        self.assertEqual(to_addrs, ["newemail@example.net"])
        self.assertEqual(
            msg["Subject"], "Login Service: Finish your registration")


class AuthTokenSetTests(SSODatabasePolicyTests):

    layer = DatabaseFunctionalLayer

    def test_get(self):
        # Test get() and __getitem__() methods of AuthTokenSet.
        authtokenset = getUtility(IAuthTokenSet)
        token = authtokenset.new(
            None, u"requester@example.net", u"newemail@example.net",
            LoginTokenType.NEWACCOUNT, None)
        Store.of(token).flush()

        self.assertEqual(authtokenset.get(token.id), token)
        self.assertEqual(authtokenset[token.token], token)

    def test_searchByEmailAccountAndType(self):
        account = self.factory.makeAccount(
            u"Test Account", status=AccountStatus.ACTIVE)
        authtokenset = getUtility(IAuthTokenSet)
        token1 = authtokenset.new(
            account, u"requester@example.net", u"newemail@example.net",
            LoginTokenType.VALIDATEEMAIL, None)
        token1.consume()
        token2 = authtokenset.new(
            account, u"otheremail@example.net", u"newemail@example.net",
            LoginTokenType.VALIDATEEMAIL, None)

        result = authtokenset.searchByEmailAccountAndType(
            u"newemail@example.net", account, LoginTokenType.VALIDATEEMAIL)
        self.assertContentEqual(result, [token1, token2])

        # The consumed argument lets us filter the returned tokens.
        result = authtokenset.searchByEmailAccountAndType(
            u"newemail@example.net", account, LoginTokenType.VALIDATEEMAIL,
            consumed=False)
        self.assertContentEqual(result, [token2])

        result = authtokenset.searchByEmailAccountAndType(
            u"newemail@example.net", account, LoginTokenType.VALIDATEEMAIL,
            consumed=True)
        self.assertContentEqual(result, [token1])

        # No tokens found if email, account or token type don't match.
        result = authtokenset.searchByEmailAccountAndType(
            u"otheremail@example.net", account, LoginTokenType.VALIDATEEMAIL)
        self.assertEqual(result.count(), 0)

        account2 = self.factory.makeAccount(
            u"Test Account 2", status=AccountStatus.ACTIVE)
        result = authtokenset.searchByEmailAccountAndType(
            u"newemail@example.net", account2, LoginTokenType.VALIDATEEMAIL)
        self.assertEqual(result.count(), 0)

        result = authtokenset.searchByEmailAccountAndType(
            u"newemail@example.net", account, LoginTokenType.PASSWORDRECOVERY)
        self.assertEqual(result.count(), 0)

    def test_deleteByEmailAccountAndType(self):
        account = self.factory.makeAccount(
            u"Test Account", status=AccountStatus.ACTIVE)
        authtokenset = getUtility(IAuthTokenSet)
        token1 = authtokenset.new(
            account, u"requester@example.net", u"newemail@example.net",
            LoginTokenType.VALIDATEEMAIL, None)
        token2 = authtokenset.new(
            account, u"otheremail@example.net", u"newemail@example.net",
            LoginTokenType.VALIDATEEMAIL, None)
        store = Store.of(token1)

        authtokenset.deleteByEmailAccountAndType(
            u"newemail@example.net", account, LoginTokenType.VALIDATEEMAIL)

        self.assertRaises(LostObjectError, store.reload, token1)
        self.assertRaises(LostObjectError, store.reload, token2)

    def test_new(self):
        account = self.factory.makeAccount(
            u"Test Account", status=AccountStatus.ACTIVE)
        # This could be any supported token type
        token_type = LoginTokenType.VALIDATEEMAIL

        token = getUtility(IAuthTokenSet).new(
            account, u"requester@example.net", u"newemail@example.net",
            token_type, u"http://redirection-url")

        self.assertProvides(token, IAuthToken)
        self.assertIsInstance(token.token, unicode)
        self.assertEqual(token.tokentype, token_type)
        self.assertEqual(token.requester_account, account)
        self.assertEqual(token.requesteremail, u"requester@example.net")
        self.assertEqual(token.email, u"newemail@example.net")
        self.assertEqual(token.date_consumed, None)
        self.assertEqual(token.redirection_url, u"http://redirection-url")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

