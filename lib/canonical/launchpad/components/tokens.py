# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Utility methods for random token generation."""

__metaclass__ = type

__all__ = [
    'create_token',
    'create_unique_token_for_table',
    ]

import random

from zope.component import getUtility

from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)


def create_token(token_length):
    """Create a random token string.

    :param token_length: Specifies how long you want the token.
    """
    characters = '0123456789bcdfghjklmnpqrstvwxzBCDFGHJKLMNPQRSTVWXZ'
    token = ''.join(
        random.choice(characters) for count in range(token_length))
    return token


def create_unique_token_for_table(token_length, table, column):
    """Create a new unique token in a table.

    Generates a token and makes sure it does not already exist in
    the table and column specified.

    :param token_length: The length for the token string
    :param table: The table to use
    :param column: The column containing the token in 'table'

    :return: A new token string
    """
    token = create_token(token_length)
    store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
    new_row = store.find(table, "%s='%s'" % (column, token)).one()
    while new_row is not None:
        token = create_token(token_length)
        new_row = store.find(table, "%s='%s'" % (column, token)).one()
    return token

