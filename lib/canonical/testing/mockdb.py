# Copyright 2007-2008 Canonical Ltd.  All rights reserved.

"""A self maintaining mock database for tests.

The first time a `MockDbConnection` is used, it functions as a proxy
to the real database connection. Queries and results are recorded into
a cache.

For subsequent runs, if the same queries are issued in the same order
then results are returned from the cached log and the real database is
not used. If the cache is detected as being invalid, it is removed and
a `RetryTest` exception raised for the test runner to deal with.
"""

__metaclass__ = type
__all__ = [
        'MockDbConnection', 'RecordCache', 'ReplayCache', 'cache_filename',
        ]

import cPickle as pickle
import gzip
import os.path
import urllib

import psycopg
from zope.testing.testrunner import RetryTest, dont_retry

from canonical.config import config


CACHE_DIR = os.path.join(config.root, 'mockdbcache~')


def cache_filename(key):
    """Calculate and return the cache filename to use."""
    key = urllib.quote(key, safe='')
    return os.path.join(CACHE_DIR, key) + '.pickle.gz'


class CacheEntry:
    """An entry in our test's log of database calls."""

    # The connection number used for this command. All connections used
    # by a test store their commands in a single list to preserve global
    # ordering, and we use connection_number to differentiate them.
    connection_number = None

    # If the command raised an exception, it is stored here.
    exception = None

    def __init__(self, connection):
        if connection is not None:
            self.connection_number = connection.connection_number


class ConnectCacheEntry(CacheEntry):
    """An entry created instantiating a Connection."""
    args = None # Arguments passed to the connect() method.
    kw = None # Keyword arguments passed to the connect() method.
    
    def __init__(self, connection, *args, **kw):
        super(ConnectCacheEntry, self).__init__(connection)
        self.args = args
        self.kw = kw


class ExecuteCacheEntry(CacheEntry):
    """An entry created via Cursor.execute()."""
    query = None # Query passed to Cursor.execute().
    params = None # Parameters passed to Cursor.execute().
    results = None # Cursor.fetchall() results as a list.
    description = None # Cursor.description as per DB-API.
    rowcount = None # Cursor.rowcount after Cursor.fetchall() as per DB-API.

    def __init__(self, connection, query, params):
        super(ExecuteCacheEntry, self).__init__(connection)
        self.query = query
        self.params = params


class CloseCacheEntry(CacheEntry):
    """An entry created via Connection.close()."""


class CommitCacheEntry(CacheEntry):
    """An entry created via Connection.commit()."""


class RollbackCacheEntry(CacheEntry):
    """An entry created via Connection.rollback()."""


class SetIsolationLevelCacheEntry(CacheEntry):
    """An entry created via Connection.set_isolation_level()."""
    level = None # The requested isolation level
    def __init__(self, connection, level):
        super(SetIsolationLevelCacheEntry, self).__init__(connection)
        self.level = level


class RecordCache:
    key = None # The unique key to this test.
    cache_filename = None # Path to our cache file.
    log = None
    connections = None

    def __init__(self, key):
        self.key = key
        self.cache_filename = cache_filename(key)
        self.log = []
        self.connections = []

    def connect(self, connect_func, *args, **kw):
        """Open a connection to the database, returning a `MockDbConnection`.
        """
        try:
            connection = connect_func(*args, **kw)
            exception = None
        except (psycopg.Warning, psycopg.Error), connect_exception:
            connection = None
            exception = connect_exception

        connection = MockDbConnection(self, connection, *args, **kw)

        self.connections.append(connection)
        if connection is not None:
            connection.connection_number = self.connections.index(connection)
        entry = ConnectCacheEntry(connection, *args, **kw)
        self.log.append(entry)
        if exception:
            entry.exception = exception
            raise exception
        return connection

    def execute(self, cursor, query, params=None):
        """Handle Cursor.execute()."""
        con = cursor.connection
        entry = ExecuteCacheEntry(con, query, params)

        real_cursor = cursor.real_cursor
        try:
            real_cursor.execute(query, params)
        except (psycopg.Warning, psycopg.Error), exception:
            entry.exception = exception
            self.log.append(entry)
            raise

        entry.rowcount = real_cursor.rowcount
        try:
            entry.results = list(real_cursor.fetchall())
            entry.description = real_cursor.description
            # Might have changed now fetchall() has been done.
            entry.rowcount = real_cursor.rowcount
        except psycopg.Error:
            # No results, such as an UPDATE query.
            entry.results = None

        self.log.append(entry)
        return entry

    def close(self, connection):
        """Handle Connection.close()."""
        entry = CloseCacheEntry(connection)
        try:
            if connection.real_connection is not None:
                connection.real_connection.close()
            self.log.append(entry)
        except (psycopg.Warning, psycopg.Error), exception:
            entry.exception = exception
            self.log.append(entry)
            raise

    def commit(self, connection):
        """Handle Connection.commit()."""
        entry = CommitCacheEntry(connection)
        try:
            connection.real_connection.commit()
            self.log.append(entry)
        except (psycopg.Warning, psycopg.Error), exception:
            entry.exception = exception
            self.log.append(entry)
            raise

    def rollback(self, connection):
        """Handle Connection.rollback()."""
        entry = RollbackCacheEntry(connection)
        try:
            connection.real_connection.rollback()
            self.log.append(entry)
        except (psycopg.Warning, psycopg.Error), exception:
            entry.exception = exception
            self.log.append(entry)
            raise

    def set_isolation_level(self, connection, level):
        """Handle Connection.set_isolation_level()."""
        entry = SetIsolationLevelCacheEntry(connection, level)
        try:
            connection.real_connection.set_isolation_level(level)
            self.log.append(entry)
        except (psycopg.Warning, psycopg.Error), exception:
            entry.exception = exception
            self.log.append(entry)
            raise

    def store(self):
        """Store the log for future runs."""
        # Create cache directory if necessary.
        if not os.path.isdir(CACHE_DIR):
            os.makedirs(CACHE_DIR, mode=0700)

        # Insert our connection parameters into the list we will pickle.
        obj_to_store = [self.key] + self.log
        pickle.dump(
                obj_to_store, gzip.open(self.cache_filename, 'wb'),
                pickle.HIGHEST_PROTOCOL
                )

        # Trash all the connected connections. This isn't strictly necessary
        # but protects us from silly mistakes.
        while self.connections:
            con = self.connections.pop()
            if con is not None and not con._closed:
                con.close()


def noop_if_invalid(func):
    """Decorator that causes the decorated method to be a noop if the
    cache this method belongs too is invalid.

    This allows teardown to complete when a ReplayCache has
    raised a RetryTest exception. Normally during teardown DB operations
    are made when doing things like aborting the transaction.
    """
    def dont_retry_func(self, *args, **kw):
        if self.invalid:
            return None
        else:
            return func(self, *args, **kw)
    return dont_retry_func


class ReplayCache:
    """Replay database queries from a cache."""

    key = None # Unique key identifying this test.
    cache_filename = None # File storing our statement/result cache.
    log = None # List of CacheEntry objects loaded from _cache_filename.
    connections = None # List of connections using this cache.

    invalid = False # If True, the cache is invalid and we are tearing down.

    def __init__(self, key):
        self.key = key
        self.cache_filename = cache_filename(key)
        self.log = pickle.load(gzip.open(self.cache_filename, 'rb'))
        try:
            stored_key = self.log.pop(0)
            assert stored_key == key, "Cache loaded for wrong key."
        except IndexError:
            self.handleInvalidCache(
                    "Connection key not stored in cache."
                    )

        self.connections = []

    def getNextEntry(self, connection, expected_entry_class):
        """Pull the next entry from the cache.

        Invokes handleInvalidCache on error, including some entry validation.
        """
        try:
            entry = self.log.pop(0)
        except IndexError:
            self.handleInvalidCache('Ran out of commands.')

        if not isinstance(entry, CacheEntry):
            self.handleInvalidCache('Unexpected object type in cache')

        if connection.connection_number != entry.connection_number:
            self.handleInvalidCache(
                    'Expected query to connection %s '
                    'but got query to connection %s'
                    % (entry.connection_number, connection.connection_number)
                    )

        if not isinstance(entry, expected_entry_class):
            self.handleInvalidCache(
                    'Expected %s but got %s'
                    % (expected_entry_class, entry.__class__)
                    )

        return entry

    @noop_if_invalid
    def connect(self, connect_func, *args, **kw):
        """Return a `MockDbConnection`.
       
        Does not actually connect to the database - we are in replay mode.
        """
        connection = MockDbConnection(self, None, *args, **kw)
        self.connections.append(connection)
        connection.connection_number = self.connections.index(connection)
        entry = self.getNextEntry(connection, ConnectCacheEntry)
        if (entry.args, entry.kw) != (args, kw):
            self.handleInvalidCache("Connection parameters have changed.")
        if entry.exception is not None:
            raise entry.exception
        return connection

    @noop_if_invalid
    def execute(self, cursor, query, params=None):
        """Handle Cursor.execute()."""
        connection = cursor.connection
        entry = self.getNextEntry(connection, ExecuteCacheEntry)

        if query != entry.query:
            self.handleInvalidCache(
                    'Unexpected command. Expected %s. Got %s.'
                    % (entry.query, query)
                    )

        if params != entry.params:
            self.handleInvalidCache(
                    'Unexpected parameters. Expected %r. Got %r.'
                    % (entry.params, params)
                    )

        if entry.exception is not None:
            raise entry.exception

        return entry

    @noop_if_invalid
    def close(self, connection):
        """Handle Connection.close()."""
        entry = self.getNextEntry(connection, CloseCacheEntry)
        if entry.exception is not None:
            raise entry.exception

    def commit(self, connection):
        """Handle Connection.commit()."""
        entry = self.getNextEntry(connection, CommitCacheEntry)
        if entry.exception is not None:
            raise entry.exception

    @noop_if_invalid
    def rollback(self, connection):
        """Handle Connection.rollback()."""
        entry = self.getNextEntry(connection, RollbackCacheEntry)
        if entry.exception is not None:
            raise entry.exception

    @noop_if_invalid
    def set_isolation_level(self, connection, level):
        """Handle Connection.set_isolation_level()."""
        entry = self.getNextEntry(connection, SetIsolationLevelCacheEntry)
        if entry.level != level:
            self.handleInvalidCache("Different isolation level requested.")
        if entry.exception is not None:
            raise entry.exception

    def handleInvalidCache(self, reason):
        """Remove the cache from disk and raise a RetryTest exception."""
        if os.path.exists(self.cache_filename):
            os.unlink(self.cache_filename)
        self.invalid = True
        raise RetryTest(reason)


class MockDbConnection:
    """Connection to our Mock database."""

    real_connection = None
    connection_number = None
    cache = None

    def __init__(self, cache, real_connection, *args, **kw):
        """Initialize the `MockDbConnection`.

        `MockDbConnection` intances are generally only created in the
        *Cache.connect() methods as the attempt needs to be recorded
        (even if it fails).

        If we have a real_connection, we are proxying and recording results.
        If real_connection is None, we are replaying results from the cache.

        *args and **kw are the arguments passed to open the real connection
        and are used by the cache to confirm the db connection details have
        not been changed; a RetryTest exception may be raised in replay mode.
        """
        self.cache = cache
        self.real_connection = real_connection

    def cursor(self):
        """As per DB-API."""
        return MockDbCursor(self)

    _closed = False

    def _checkClosed(self):
        """Guard that raises an exception if the connection is closed."""
        if self._closed is True:
            raise psycopg.Error('Connection closed.')

    def close(self):
        """As per DB-API."""
        # DB-API says closing a closed connection should raise an exception
        # ("exception will be raised if any operation is attempted
        # wht the [closed] connection"), but psycopg1 doesn't do this.
        # It would be nice if our wrapper could be more strict than psycopg1,
        # but unfortunately the sqlos/sqlobject combination relies on this
        # behavior. So we have to emulate it.
        if self._closed:
            return
        self._checkClosed()
        self.cache.close(self)
        self._closed = True

    def commit(self):
        """As per DB-API."""
        self._checkClosed()
        self.cache.commit(self)

    def rollback(self):
        """As per DB-API."""
        self._checkClosed()
        self.cache.rollback(self)

    def set_isolation_level(self, level):
        """As per psycopg1 extension."""
        self._checkClosed()
        self.cache.set_isolation_level(self, level)

    # Exceptions exposed on connection, as per optional DB-API extension.
    ## Disabled, as psycopg1 does not implement this extension.
    ## Warning = psycopg.Warning
    ## Error = psycopg.Error
    ## InterfaceError = psycopg.InterfaceError
    ## DatabaseError = psycopg.DatabaseError
    ## DataError = psycopg.DataError
    ## OperationalError = psycopg.OperationalError
    ## IntegrityError = psycopg.IntegrityError
    ## InternalError = psycopg.InternalError
    ## ProgrammingError = psycopg.ProgrammingError
    ## NotSupportedError = psycopg.NotSupportedError


class MockDbCursor:
    _cache_entry = None

    arraysize = 100 # As per DB-API.
    connection = None # As per DB-API optional extension.

    def __init__(self, connection):
        self.connection = connection

    @property
    def description(self):
        """As per DB-API, pulled from the cache entry."""
        if self._cache_entry is None:
            return None
        return self._cache_entry.description

    @property
    def rowcount(self):
        """Return the rowcount only if all the results have been consumed.
       
        As per DB-API, pulled from the cache entry.
        """
        if not isinstance(self._cache_entry, ExecuteCacheEntry):
            return -1

        results = self._cache_entry.results

        if results is None: # DELETE or UPDATE set rowcount.
            return self._cache_entry.rowcount
        
        if results is None or self._fetch_position < len(results):
            return -1
        return self._cache_entry.rowcount

    _real_cursor = None # Used by real_cursor().

    @property
    def real_cursor(self):
        """A real DB cursor is needed. Return it."""
        self._checkClosed()
        if self._real_cursor is None:
            self._real_cursor = self.connection.real_connection.cursor()
        return self._real_cursor

    _closed = False

    def close(self):
        """As per DB-API."""
        self._checkClosed()
        self._closed = True
        if self._real_cursor is not None:
            self._real_cursor.close()
            self._real_cursor = None
            self.connection = None

    def _checkClosed(self):
        """Raise an exception if the cursor or connection is closed."""
        if self._closed is True:
            raise psycopg.Error('Cursor closed.')
        self.connection._checkClosed()

    # Index in our results that the next fetch will return. We don't consume
    # the results list as if we are recording we need to serialize the results
    # when the test is completed. 
    _fetch_position = 0

    def execute(self, query, parameters=None):
        """As per DB-API."""
        self._checkClosed()
        self._cache_entry = self.connection.cache.execute(
                self, query, parameters
                )
        self._fetch_position = 0

    def executemany(self, query, seq_of_parameters=None):
        """As per DB-API."""
        self._checkClosed()
        raise NotImplementedError('executemany')

    def fetchone(self):
        """As per DB-API."""
        self._checkClosed()
        if self._cache_entry is None:
            raise psycopg.Error("No query issued yet")
        if self._cache_entry.results is None:
            raise psycopg.Error("Query returned no results")
        try:
            row = self._cache_entry.results[self._fetch_position]
            self._fetch_position += 1
            return row
        except IndexError:
            return None

    def fetchmany(self, size=None):
        """As per DB-API."""
        self._checkClosed()
        if size is None:
            size = self.arraysize
        raise NotImplementedError('fetchmany')

    def fetchall(self):
        """As per DB-API."""
        self._checkClosed()
        if self._cache_entry is None:
            raise psycopg.Error('No query issued yet')
        if self._cache_entry.results is None:
            raise psycopg.Error('Query returned no results')
        results = self._cache_entry.results[self._fetch_position:]
        self._fetch_position = len(results)
        return results

    def nextset(self):
        """As per DB-API."""
        self._checkClosed()
        raise NotImplementedError('nextset')

    def setinputsizes(self, sizes):
        """As per DB-API."""
        self._checkClosed()
        return # No-op.

    def setoutputsize(self, size, column=None):
        """As per DB-API."""
        self._checkClosed()
        return # No-op.

    ## psycopg1 does not support this extension.
    ##
    ## def next(self):
    ##     """As per iterator spec and DB-API optional extension."""
    ##     row = self.fetchone()
    ##     if row is None:
    ##         raise StopInteration
    ##     else:
    ##         return row

    ## def __iter__(self):
    ##     """As per iterator spec and DB-API optional extension."""
    ##     return self

