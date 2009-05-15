# Copyright 2009 Canonical Ltd.  All rights reserved.

"""OpenID Consumer related database classes."""

__metaclass__ = type
__all__ = ['BaseOpenIDStore', 'OpenIDConsumerNonce']

from openid.store.sqlstore import PostgreSQLStore
import psycopg2
from storm.locals import DateTime, Int, Storm, Unicode
from zope.component import getUtility
from zope.interface import implements, classProvides

from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, MASTER_FLAVOR)
from canonical.launchpad.interfaces.openidconsumer import (
    IOpenIDConsumerStoreFactory)


class OpenIDConsumerNonce(Storm):
    """An OpenIDNonce.

    The table definition matches that required by the openid library,
    so doesn't follow our standards. In particular, it doesn't have an
    id column and the timestamp is an epoch time integer rather than a
    datetime.
    """
    __storm_table__ = "OpenIDConsumerNonce"
    __storm_primary__ = "server_url", "timestamp", "salt"

    server_url = Unicode()
    timestamp = Int()
    salt = Unicode()


class BaseOpenIDStore(PostgreSQLStore):
    """The standard OpenID Library PostgreSQL store with overrides to
    ensure it plays nicely with Zope3 and Launchpad.
    """
    classProvides(IOpenIDConsumerStoreFactory)

    exceptions = psycopg2
    settings_table = None

    associations_table = None # Override.
    nonces_table = None # Override.
    storm_store = None # Override.

    def __init__(self):
        # No need to pass in the connection - we have better ways of
        # getting a cursor.
        PostgreSQLStore.__init__(self, None)

    def _callInTransaction(self, func, *args, **kwargs):
        """Open a fresh cursor and call the given method.

        No transactional semantics in Launchpad because Z3 is already
        fully transactional so there is no need to reinvent the wheel.
        """
        # We seem to need to force the use of the master store here,
        # as we need to write on GET.
        connection = getUtility(IStoreSelector).get(
            self.storm_store, MASTER_FLAVOR)._connection
        connection._ensure_connected()
        try:
            self.cur = connection._check_disconnect(
                connection._raw_connection.cursor)
            return connection._check_disconnect(func, *args, **kwargs)
        finally:
            self.cur = None

    def createTables(self):
        """Not desired in Launchpad - raise an exception."""
        raise AssertionError("Tables should not be created automatically")

    txn_createTables = createTables


class OpenIDConsumerStore(BaseOpenIDStore):
    """The standard OpenID Library PostgreSQL store with overrides to
    ensure it plays nicely with Zope3 and Launchpad.

    `BaseOpenIDStore` for use by Launchpad as an OpenID client.

    It is registered as a factory to provide a way for instances to be
    created from browser code without warnings; getUtility is not
    suitable as this class is not thread safe.
    """
    classProvides(IOpenIDConsumerStoreFactory)
    associations_table = 'OpenIDConsumerAssociation'
    nonces_table = 'OpenIDConsumerNonce'
    store = MAIN_STORE
