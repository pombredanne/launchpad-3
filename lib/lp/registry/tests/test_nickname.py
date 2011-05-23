# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for nickname generation"""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.model.person import (
    generate_nick,
    NicknameGenerationError,
    )
from lp.testing import TestCaseWithFactory


class TestNicknameGeneration(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_rejects_invalid_emails(self):
        # generate_nick rejects invalid email addresses
        self.assertRaises(
            NicknameGenerationError,
            generate_nick,
            'foo@example@com')

    def test_uses_email_address(self):
        # generate_nick uses the first part of the email address to create
        # the nick.
        nick = generate_nick('bar@example.com')
        self.assertEqual('bar', nick)

    def test_does_not_start_nick_with_symbols(self):
        # If an email starts with symbols, generate_nick still creates a
        # valid nick that doesn't start with symbols.
        nick = generate_nick('---bar@example.com')
        self.assertEqual('bar', nick)

    def test_enforces_minimum_length(self):
        # Nicks must be a minimum of four characters. generate_nick creates
        # nicks over a that length.
        nick = generate_nick('i@example.com')
        self.assertEqual('i-example', nick)

    def test_can_create_noncolliding_nicknames(self):
        # Given the same email address, generate_nick doesn't recreate the
        # same nick once that nick is used.
        self._useNicknames(['bar'])
        nick = generate_nick('bar@example.com')
        self.assertEqual('bar-example', nick)

        self._useNicknames(['bar-example', 'bar-example-com'])
        self.assertNotIn(nick, ['bar', 'bar-example', 'bar-example-com'])

    def _useNicknames(self, nicknames):
        # Helper method to consume a nickname
        for nick in nicknames:
            self.factory.makePerson(name=nick)
        #flush_database_updates()
