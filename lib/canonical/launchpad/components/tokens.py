# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Utility methods for random token generation."""

__metaclass__ = type

__all__ = [
    'create_token',
    'create_unique_token_for_table',
    ]

import random

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
    new_row = table.selectOneBy(**{column:token})
    while new_row is not None:
        token = create_token(token_length)
        new_row = table.selectOneBy(**{column:token})
    return token

