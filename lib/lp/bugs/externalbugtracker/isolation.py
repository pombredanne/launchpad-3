# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Ensure that some operations happen outside of transactions."""

__metaclass__ = type
__all__ = [
    'is_transaction_in_progress',
    'ensure_no_transaction',
    ]

from functools import wraps

import transaction


class TransactionInProgress(Exception):
    """Transactions may not be open at the same time as a blocking
    operation."""


def is_transaction_in_progress():
    # Accessing private attributes is naughty.
    return len(transaction.get()._resources) != 0


def ensure_no_transaction(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if is_transaction_in_progress():
            raise TransactionInProgress()
        return func(*args, **kwargs)
    return wrapper
