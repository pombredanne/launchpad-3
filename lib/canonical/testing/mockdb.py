# Copyright 2007 Canonical Ltd.  All rights reserved.

"""A self maintaining mock database for tests.

The first time a MockDbConnection with a given key is used,
it functions as a proxy to the real database connection. Queries
and results are recorded into a cache.

For subsequent runs, if the same queries are issued in the same order
then results are returned from the cached log and the real database
not used. If the cache is detected as being invalid, it is removed and
a RetryTest exception raised for the test runner to deal with.
"""

__metaclass__ = type
__all__ = []

import cPickle as pickle
import gzip
import os.path

import psycopg

from canonical.config import config


CACHE_DIR = os.path.join(config.root, 'mockdbcache~')


class RetryTest(Exception):
    """Exception indicating the current test should be aborted and retried."""


def cache_filename(key):
    """Calculate and return the cache filename to use."""
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
        self.connection_number = connection.connection_number


class ExecuteCacheEntry(CacheEntry):
    """An entry created via Cursor.execute()."""
    query = None # Query passed to Cursor.execute()
    params = None # Parameters passed to Cursor.execute()
    results = None # Cursor.fetchall() results as a list
    description = None # Cursor.description as per DB-API
    rowcount = None # Cursor.rowcount after Cursor.fetchall() as per DB-API


class CloseCacheEntry(CacheEntry):
    """An entry created via Connection.close()."""


class CommitCacheEntry(CacheEntry):
    """An entry created via Connection.commit()."""


class RollbackCacheEntry(CacheEntry):
    """An entry created via Connection.rollback()."""


class ReplayCache:
    """Replay database queries from a cache."""

    cache_filename = None # File storing our statement/result cache
    log = None # List of CacheEntry objects loaded from _cache_filename
    connections = None # List of connections using this cache

    def __init__(self, cache_filename):
        self.cache_filename = cache_filename
        self.log = pickle.load(gzip.open(cache_filename, 'rb'))
        self.connections = []

    def getNextEntry(self, connection, expected_entry_class):
        """Pull the next entry from the cache.

        Invokes handleInvalidCache on error, including some entry validation.
        """
        try:
            entry = self.log.pop(0)
        except IndexError:
            self.handleInvalidCache('Ran out of commands.')
        assert isinstance(entry, CacheEntry), 'Unknown object in cache'

        if connection.connection_number != entry.connection_number:
            self.handleInvalidCache(
                    'Expected query to connection %d '
                    'but got query to connection %d'
                    % (entry.connection_number, connection.connection_number)
                    )

        if not isinstance(entry, expected_entry_class):
            self.handleInvalidCache(
                    'Expected %s but got %s'
                    % (expected_entry_class, entry.__class__)
                    )

        return entry

    def execute(self, cursor, query, params=None):
        """Handle Cursor.execute()."""
        connection = cursor.connection
        entry = self.getNextEntry(connection, ExecuteCacheEntry)

        if query != entry.query:
            self.handleInvalidCache(
                    'Unexpected command. Expected %s. Got %s.'
                    % (entry.sql_command, command)
                    )

        if params != entry.params:
            self.handleInvalidCache(
                    'Unexpected parameters. Expected %r. Got %r.'
                    % (entry.params, params)
                    )

        if entry.exception is not None:
            raise entry.exception

        return entry

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

    def rollback(self, connection):
        """Handle Connection.rollback()."""
        entry = self.getNextEntry(connection, RollbackCacheEntry)
        if entry.exception is not None:
            raise entry.exception

    def handleInvalidCache(self, reason):
        """Remove the cache from disk and raise a RetryTest exception."""
        os.unlink(self.cache_filename)
        raise RetryTest(reason)


class RecordCache:
    cache_filename = None
    log = None
    connections = None

    def __init__(self, cache_filename):
        self.cache_filename = cache_filename
        self.log = []
        self.connections = []

    def execute(self, cursor, query, params=None):
        """Handle Cursor.execute()."""
        con = cursor.connection
        entry = ExecuteCacheEntry(con)
        entry.query = query
        entry.params = params

        real_cursor = cursor.real_cursor
        try:
            real_cursor.execute(query, params)
        except (con.Warning, con.Error), exception:
            entry.exception = exception
            self.log.append(entry)
            raise

        try:
            entry.results = list(real_cursor.fetchall())
            entry.rowcount = real_cursor.rowcount
            entry.description = real_cursor.description
        except con.Error:
            # No results, such as an UPDATE query
            entry.results = None

        self.log.append(entry)
        return entry

    def close(self, connection):
        """Handle Connection.close()."""
        entry = CloseCacheEntry(connection)
        try:
            connection.real_connection.close()
            self.log.append(entry)
        except (connection.Warning, connection.Error), exception:
            entry.exception = exception
            self.log.append(entry)
            raise

    def commit(self, connection):
        """Handle Connection.commit()."""
        entry = CommitCacheEntry(connection)
        try:
            connection.real_connection.commit()
            self.log.append(entry)
        except (connection.Warning, connection.Error), exception:
            entry.exception = exception
            self.log.append(entry)

    def rollback(self, connection):
        """Handle Connection.rollback()."""
        entry = RollbackCacheEntry(connection)
        try:
            connection.real_connection.rollback()
            self.log.append(entry)
        except (connection.Warning, connection.Error), exception:
            entry.exception = exception
            self.log.append(entry)

    def store(self):
        """Store the log for future runs."""
        # Create cache directory if necessary
        if not os.path.isdir(CACHE_DIR):
            os.makedirs(CACHE_DIR, mode=0700)
        pickle.dump(
                self.log, gzip.open(self.cache_filename, 'wb'),
                pickle.HIGHEST_PROTOCOL
                )

        # Trash all the connected connections. This isn't strictly necessary
        # but protects us from silly mistakes.
        while self.connections:
            con = self.connections.pop()
            if not con._closed:
                con.close()


class MockDbConnection:
    """Connection to our Mock database."""

    real_connection = None
    connection_number = None
    cache = None

    def __init__(self, cache, real_connection=None):
        """Initialize the MockDbConnection.

        If we have a real_connection, we are proxying and recording results.
        If real_connection is None, we are replaying results from the cache.
        """
        self.cache = cache
        if isinstance(cache, ReplayCache):
            assert real_connection is None, \
                    'Passed a real db connection in replay mode.'
        else:
            self.real_connection = real_connection

        cache.connections.append(self)
        self.connection_number = cache.connections.index(self)

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
        # DB-API says an exception should be raised if closing an already
        # closed connection, but psycopg1 doesn't follow the spec here.
        if self._closed is True:
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

    # Exceptions exposed on connection, as per optional DB-API extension
    Warning = psycopg.Warning
    Error = psycopg.Error
    InterfaceError = psycopg.InterfaceError
    DatabaseError = psycopg.DatabaseError
    DataError = psycopg.DataError
    OperationalError = psycopg.OperationalError
    IntegrityError = psycopg.IntegrityError
    InternalError = psycopg.InternalError
    ProgrammingError = psycopg.ProgrammingError
    NotSupportedError = psycopg.NotSupportedError

class MockDbCursor:
    _cache_entry = None

    arraysize = 100 # As per DB-API
    connection = None # As per DB-API optional extension

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
        if self._cache_entry is None:
            return -1
        results = self._cache_entry.results
        if results is None or self._fetch_position < len(results):
            return -1
        return self._cache_entry.rowcount

    _real_cursor = None # Used by real_cursor()

    @property
    def real_cursor(self):
        """A real DB cursor is needed. Return it."""
        self._checkClosed()
        if self._real_cursor is None:
            self._real_cursor = self.connection.real_connection.cursor()
        return self._real_cursor

    _closed = False

    def close(self):
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
        return # No-op

    def setoutputsize(self, size, column=None):
        """As per DB-API."""
        self._checkClosed()
        return # No-op

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

