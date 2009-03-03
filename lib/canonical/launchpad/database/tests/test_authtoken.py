# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for AuthToken code."""

__metaclass__ = type

import email
import unittest

from storm.store import Store
import transaction
from zope.component import getUtility

from canonical.launchpad.database.authtoken import AuthToken
from canonical.launchpad.interfaces.account import AccountStatus
from canonical.launchpad.interfaces.authtoken import (
    IAuthToken, IAuthTokenSet, LoginTokenType)
from canonical.launchpad.mail import stub
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.testing import DatabaseFunctionalLayer


class AuthTokenTests(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_create(self):
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

    def test_consume(self):
        account = self.factory.makeAccount(
            u"Test Account", status=AccountStatus.ACTIVE)
        token_type = LoginTokenType.VALIDATEEMAIL

        token1 = getUtility(IAuthTokenSet).new(
            account, u"requester@example.net", u"newemail@example.net",
            token_type)
        token2 = getUtility(IAuthTokenSet).new(
            account, u"requester@example.net", u"newemail@example.net",
            token_type)
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
            LoginTokenType.VALIDATEEMAIL)
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
            LoginTokenType.PASSWORDRECOVERY)
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
            LoginTokenType.NEWACCOUNT)
        token.sendNewUserEmail()
        transaction.commit()

        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        msg = email.message_from_string(raw_msg)

        self.assertEqual(to_addrs, ["newemail@example.net"])
        self.assertEqual(
            msg["Subject"], "Login Service: Finish your registration")


class AuthTokenSetTests(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

