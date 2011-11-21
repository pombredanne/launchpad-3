# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import random
import testtools

from canonical.database.constants import UTC_NOW
from canonical.launchpad.components.tokens import (
    create_token,
    create_unique_token_for_table,
    )
from canonical.launchpad.database.logintoken import LoginToken
from canonical.launchpad.interfaces.authtoken import LoginTokenType
from canonical.testing.layers import DatabaseFunctionalLayer


class Test_create_token(testtools.TestCase):

    def test_length(self):
        token = create_token(99)
        self.assertEquals(len(token), 99)


class Test_create_unique_token_for_table(testtools.TestCase):
    layer = DatabaseFunctionalLayer

    def test_token_uniqueness(self):
        # Since the prng will be seeded in this test it is important we clean
        # up by calling seed with no parameters, which will use OS-provided
        # entropy if available or use the system clock.
        self.addCleanup(random.seed)
        # Calling create_unique_token_for_table() twice with the same
        # random.seed() will generate two identical tokens, as the token was
        # never inserted in the table.
        random.seed(0)
        token1 = create_unique_token_for_table(99, LoginToken.token)
        random.seed(0)
        token2 = create_unique_token_for_table(99, LoginToken.token)
        self.assertEquals(token1, token2)

        # Now insert the token in the table so that the next time we call
        # create_unique_token_for_table() we get a different token.
        LoginToken(
            requester=None, token=token2, email='email@example.com',
            tokentype=LoginTokenType.ACCOUNTMERGE, created=UTC_NOW)
        random.seed(0)
        token3 = create_unique_token_for_table(99, LoginToken.token)
        self.assertNotEquals(token1, token3)
