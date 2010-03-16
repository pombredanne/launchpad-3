# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Ensure that some operations happen outside of transactions."""

__metaclass__ = type
__all__ = [
    'ensure_no_transaction',
    ]

import psycopg2.extensions

from functools import wraps

from zope.component import getUtility

from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, MASTER_FLAVOR)


TRANSACTION_IN_PROGRESS_STATUSES = frozenset((
        psycopg2.extensions.TRANSACTION_STATUS_ACTIVE,
        psycopg2.extensions.TRANSACTION_STATUS_INTRANS,
        psycopg2.extensions.TRANSACTION_STATUS_INERROR,
    ))


class TransactionInProgress(Exception):
    """Transactions may not be open at the same time as a blocking
    operation."""


def is_transaction_in_progress():
    store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
    raw_connection = store._connection._raw_connection
    transaction_status = raw_connection.get_transaction_status()
    return (transaction_status in TRANSACTION_IN_PROGRESS_STATUSES)


def ensure_no_transaction(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if is_transaction_in_progress():
            raise TransactionInProgress()
        return func(*args, **kwargs)
    return wrapper
