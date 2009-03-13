# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import random
import unittest

from canonical.database.constants import UTC_NOW
from canonical.testing import DatabaseFunctionalLayer
from canonical.launchpad.components.tokens import (
    create_token, create_unique_token_for_table)
from canonical.launchpad.database.logintoken import LoginToken
from canonical.launchpad.interfaces.logintoken import LoginTokenType


class Test_create_token(unittest.TestCase):

    def test_length(self):
        token = create_token(99)
        self.assertEquals(len(token), 99)


class Test_create_unique_token_for_table(unittest.TestCase):
    layer = DatabaseFunctionalLayer

    def test_token_uniqueness(self):
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
        login_token = LoginToken(
            requester=None, token=token2, email='email@example.com',
            tokentype=LoginTokenType.NEWACCOUNT, created=UTC_NOW)
        random.seed(0)
        token3 = create_unique_token_for_table(99, LoginToken.token)
        self.assertNotEquals(token1, token3)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
