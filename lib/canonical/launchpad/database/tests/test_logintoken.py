# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the logintoken module."""

__metaclass__ = type

import doctest
from textwrap import dedent

from testtools.matchers import DocTestMatches
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.authtoken import LoginTokenType
from canonical.launchpad.interfaces.logintoken import ILoginTokenSet
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


class TestLoginToken(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_sendMergeRequestEmail(self):
        # sendMergeRequestEmail() sends an email to the user informing him/her
        # of the request.

        user1 = self.factory.makePerson(name="requester")
        user2 = self.factory.makePerson(name="duplicate", displayname="Bob")

        with person_logged_in(user1):
            token = getUtility(ILoginTokenSet).new(
                user1, user1.preferredemail.email, user2.preferredemail.email,
                LoginTokenType.ACCOUNTMERGE)

        expected_message = dedent("""
            Hello

            Launchpad: request to merge accounts
            ------------------------------------

            Someone has asked us to merge one of your Launchpad
            accounts with another.

            If you go ahead, this will merge the account called
            'Bob (duplicate)' into the account 'requester'.

            To confirm you want to do this, please follow
            this link:

                http://launchpad.dev/token/...

            If you didn't ask to merge these accounts, please
            either ignore this email or report it to the
            Launchpad team: feedback@launchpad.net

            You can read more about merging accounts in our
            help wiki:

                https://help.launchpad.net/YourAccount/Merging

            Thank you,

            The Launchpad team
            https://launchpad.net
            """)
        expected_matcher = DocTestMatches(
            expected_message, doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE)

        def _send_email(from_name, subject, message):
            self.assertEqual(
                "Launchpad Account Merge", from_name)
            self.assertEqual(
                "Launchpad: Merge of Accounts Requested", subject)
            self.assertThat(message, expected_matcher)

        # Patch our custom _send_email onto the login token.
        removeSecurityProxy(token)._send_email = _send_email

        token.sendMergeRequestEmail()
