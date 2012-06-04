# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Provides helpers for managing database triggers in tests."""

__metaclass__ = type

__all__ = [
    'disable_trigger',
    'enable_trigger',
    'triggers_disabled',
    ]

from contextlib import contextmanager

from zope.component import getUtility

from lp.services.database.sqlbase import quote_identifier
from lp.services.webapp.interfaces import (
    IStoreSelector,
    MAIN_STORE,
    MASTER_FLAVOR,
    )
from lp.testing.dbuser import dbuser


def disable_trigger(table, trigger):
    store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
    store.execute(
        'ALTER TABLE %s DISABLE TRIGGER %s'
        % (quote_identifier(table), quote_identifier(trigger)))


def enable_trigger(table, trigger):
    store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
    store.execute(
        'ALTER TABLE %s ENABLE TRIGGER %s'
        % (quote_identifier(table), quote_identifier(trigger)))


@contextmanager
def triggers_disabled(triggers):
    """A context manager that temporarily disables selected triggers.

    This commits and starts a new transaction.

    :param triggers: sequence of (table, trigger) tuples to disable.
    """
    with dbuser('postgres'):
        for trigger in triggers:
            disable_trigger(*trigger)
    yield
    with dbuser('postgres'):
        for trigger in triggers:
            enable_trigger(*trigger)
