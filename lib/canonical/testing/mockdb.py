# Copyright 2007-2008 Canonical Ltd.  All rights reserved.

"""A self maintaining mock database for tests.

The first time a `MockDbConnection` is used, it functions as a proxy
to the real database connection. Queries and results are recorded into
a script.

For subsequent runs, if the same queries are issued in the same order
then results are returned from the script and the real database is
not used. If the script is detected as being invalid, it is removed and
a `RetryTest` exception raised for the test runner to deal with.
"""

__metaclass__ = type
__all__ = [
        'MockDbConnection', 'script_filename',
        'ScriptPlayer', 'ScriptRecorder',
        ]

import cPickle as pickle
import gzip
import os.path
import urllib

import psycopg2
from zope.testing.testrunner import RetryTest

from canonical.config import config


SCRIPT_DIR = os.path.join(config.root, 'mockdbscripts~')


def script_filename(key):
    """Calculate and return the script filename to use."""
    key = urllib.quote(key, safe='')
    return os.path.join(SCRIPT_DIR, key) + '.pickle.gz'


class ScriptEntry:
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


class ConnectScriptEntry(ScriptEntry):
    """An entry created instantiating a Connection."""
    args = None # Arguments passed to the connect() method.
    kw = None # Keyword arguments passed to the connect() method.
    
    def __init__(self, connection, *args, **kw):
        super(ConnectScriptEntry, self).__init__(connection)
        self.args = args
        self.kw = kw


class ExecuteScriptEntry(ScriptEntry):
    """An entry created via Cursor.execute()."""
    query = None # Query passed to Cursor.execute().
    params = None # Parameters passed to Cursor.execute().
    results = None # Cursor.fetchall() results as a list.
    description = None # Cursor.description as per DB-API.
    rowcount = None # Cursor.rowcount after Cursor.fetchall() as per DB-API.

    def __init__(self, connection, query, params):
        super(ExecuteScriptEntry, self).__init__(connection)
        self.query = query
        self.params = params


class CloseScriptEntry(ScriptEntry):
    """An entry created via Connection.close()."""


class CommitScriptEntry(ScriptEntry):
    """An entry created via Connection.commit()."""


class RollbackScriptEntry(ScriptEntry):
    """An entry created via Connection.rollback()."""


class SetIsolationLevelScriptEntry(ScriptEntry):
    """An entry created via Connection.set_isolation_level()."""
    level = None # The requested isolation level
    def __init__(self, connection, level):
        super(SetIsolationLevelScriptEntry, self).__init__(connection)
        self.level = level


class ScriptRecorder:
    key = None # A unique key identifying this test.
    script_filename = None # Path to our script file.
    log = None
    connections = None

    def __init__(self, key):
        self.key = key
        self.script_filename = script_filename(key)
        self.log = []
        self.connections = []

    def connect(self, connect_func, *args, **kw):
        """Open a connection to the database, returning a `MockDbConnection`.
        """
        try:
            connection = connect_func(*args, **kw)
            exception = None
        except (psycopg2.Warning, psycopg2.Error), connect_exception:
            connection = None
            exception = connect_exception

        connection = MockDbConnection(self, connection, *args, **kw)

        self.connections.append(connection)
        if connection is not None:
            connection.connection_number = self.connections.index(connection)
        entry = ConnectScriptEntry(connection, *args, **kw)
        self.log.append(entry)
        if exception:
            entry.exception = exception
            #pylint: disable-msg=W0706
            raise exception
        return connection

    def cursor(self, connection):
        """Return a MockDbCursor."""
        real_cursor = connection.real_connection.cursor()
        return MockDbCursor(connection, real_cursor)

    def execute(self, cursor, query, params=None):
        """Handle Cursor.execute()."""
        con = cursor.connection
        entry = ExecuteScriptEntry(con, query, params)

        real_cursor = cursor.real_cursor
        try:
            real_cursor.execute(query, params)
        except (psycopg2.Warning, psycopg2.Error), exception:
            entry.exception = exception
            self.log.append(entry)
            raise

        entry.rowcount = real_cursor.rowcount
        try:
            entry.results = list(real_cursor.fetchall())
            entry.description = real_cursor.description
            # Might have changed now fetchall() has been done.
            entry.rowcount = real_cursor.rowcount
        except (psycopg2.InterfaceError, psycopg2.DatabaseError,
                psycopg2.Warning):
            raise
        except psycopg2.Error:
            # No results, such as an UPDATE query.
            entry.results = None

        self.log.append(entry)
        return entry

    def close(self, connection):
        """Handle Connection.close()."""
        entry = CloseScriptEntry(connection)
        try:
            if connection.real_connection is not None:
                connection.real_connection.close()
        except (psycopg2.Warning, psycopg2.Error), exception:
            entry.exception = exception
            self.log.append(entry)
            raise
        else:
            self.log.append(entry)

    def commit(self, connection):
        """Handle Connection.commit()."""
        entry = CommitScriptEntry(connection)
        try:
            connection.real_connection.commit()
        except (psycopg2.Warning, psycopg2.Error), exception:
            entry.exception = exception
            self.log.append(entry)
            raise
        else:
            self.log.append(entry)

    def rollback(self, connection):
        """Handle Connection.rollback()."""
        entry = RollbackScriptEntry(connection)
        try:
            connection.real_connection.rollback()
        except (psycopg2.Warning, psycopg2.Error), exception:
            entry.exception = exception
            self.log.append(entry)
            raise
        else:
            self.log.append(entry)

    def set_isolation_level(self, connection, level):
        """Handle Connection.set_isolation_level()."""
        entry = SetIsolationLevelScriptEntry(connection, level)
        try:
            connection.real_connection.set_isolation_level(level)
        except (psycopg2.Warning, psycopg2.Error), exception:
            entry.exception = exception
            self.log.append(entry)
            raise
        else:
            self.log.append(entry)

    def store(self):
        """Store the script for future use by a ScriptPlayer."""
        # Create script directory if necessary.
        if not os.path.isdir(SCRIPT_DIR):
            os.makedirs(SCRIPT_DIR, mode=0700)

        # Save log to a pickle. The pickle contains the key for this test,
        # followed by a list of ScriptEntry-derived objects.
        obj_to_store = [self.key] + self.log
        pickle.dump(
                obj_to_store, gzip.open(self.script_filename, 'wb'),
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
    script this method belongs too is invalid.

    This allows teardown to complete when a ReplayScript has
    raised a RetryTest exception. Normally during teardown DB operations
    are made when doing things like aborting the transaction.
    """
    def dont_retry_func(self, *args, **kw):
        if self.invalid:
            return None
        else:
            return func(self, *args, **kw)
    return dont_retry_func


class ScriptPlayer:
    """Replay database queries from a script."""

    key = None # Unique key identifying this test.
    script_filename = None # File storing our statement/result script.
    log = None # List of ScriptEntry objects loaded from _script_filename.
    connections = None # List of connections using this script.

    invalid = False # If True, the script is invalid and we are tearing down.

    def __init__(self, key):
        self.key = key
        self.script_filename = script_filename(key)
        self.log = pickle.load(gzip.open(self.script_filename, 'rb'))
        try:
            stored_key = self.log.pop(0)
            assert stored_key == key, "Script loaded for wrong key."
        except IndexError:
            self.handleInvalidScript(
                    "Connection key not stored in script."
                    )

        self.connections = []

    def getNextEntry(self, connection, expected_entry_class):
        """Pull the next entry from the script.

        Invokes handleInvalidScript on error, including some entry validation.
        """
        try:
            entry = self.log.pop(0)
        except IndexError:
            self.handleInvalidScript('Ran out of commands.')

        # This guards against file format changes as well as file corruption.
        if not isinstance(entry, ScriptEntry):
            self.handleInvalidScript('Unexpected object type in script')

        if connection.connection_number != entry.connection_number:
            self.handleInvalidScript(
                    'Expected query to connection %s '
                    'but got query to connection %s'
                    % (entry.connection_number, connection.connection_number)
                    )

        if not isinstance(entry, expected_entry_class):
            self.handleInvalidScript(
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
        entry = self.getNextEntry(connection, ConnectScriptEntry)
        if (entry.args, entry.kw) != (args, kw):
            self.handleInvalidScript("Connection parameters have changed.")
        if entry.exception is not None:
            raise entry.exception
        return connection

    def cursor(self, connection):
        """Return a MockDbCursor."""
        return MockDbCursor(connection, real_cursor=None)

    @noop_if_invalid
    def execute(self, cursor, query, params=None):
        """Handle Cursor.execute()."""
        connection = cursor.connection
        entry = self.getNextEntry(connection, ExecuteScriptEntry)

        if query != entry.query:
            self.handleInvalidScript(
                    'Unexpected command. Expected %s. Got %s.'
                    % (entry.query, query)
                    )

        if params != entry.params:
            self.handleInvalidScript(
                    'Unexpected parameters. Expected %r. Got %r.'
                    % (entry.params, params)
                    )

        if entry.exception is not None:
            raise entry.exception

        return entry

    @noop_if_invalid
    def close(self, connection):
        """Handle Connection.close()."""
        entry = self.getNextEntry(connection, CloseScriptEntry)
        if entry.exception is not None:
            raise entry.exception

    def commit(self, connection):
        """Handle Connection.commit()."""
        entry = self.getNextEntry(connection, CommitScriptEntry)
        if entry.exception is not None:
            raise entry.exception

    @noop_if_invalid
    def rollback(self, connection):
        """Handle Connection.rollback()."""
        entry = self.getNextEntry(connection, RollbackScriptEntry)
        if entry.exception is not None:
            raise entry.exception

    @noop_if_invalid
    def set_isolation_level(self, connection, level):
        """Handle Connection.set_isolation_level()."""
        entry = self.getNextEntry(connection, SetIsolationLevelScriptEntry)
        if entry.level != level:
            self.handleInvalidScript("Different isolation level requested.")
        if entry.exception is not None:
            raise entry.exception

    def handleInvalidScript(self, reason):
        """Remove the script from disk and raise a RetryTest exception."""
        if os.path.exists(self.script_filename):
            os.unlink(self.script_filename)
        self.invalid = True
        raise RetryTest(reason)


class MockDbConnection:
    """Connection to our Mock database."""

    real_connection = None
    connection_number = None
    script = None

    def __init__(self, script, real_connection, *args, **kw):
        """Initialize the `MockDbConnection`.

        `MockDbConnection` intances are generally only created in the
        *Script.connect() methods as the attempt needs to be recorded
        (even if it fails).

        If we have a real_connection, we are proxying and recording results.
        If real_connection is None, we are replaying results from the script.

        *args and **kw are the arguments passed to open the real connection
        and are used by the script to confirm the db connection details have
        not been changed; a `RetryTest` exception may be raised in replay mode.
        """
        self.script = script
        self.real_connection = real_connection

    def cursor(self):
        """As per DB-API."""
        return self.script.cursor(self)

    _closed = False

    def _checkClosed(self):
        """Guard that raises an exception if the connection is closed."""
        if self._closed is True:
            raise psycopg2.InterfaceError('Connection closed.')

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
        #self._checkClosed()
        self.script.close(self)
        self._closed = True

    def commit(self):
        """As per DB-API."""
        self._checkClosed()
        self.script.commit(self)

    def rollback(self):
        """As per DB-API."""
        self._checkClosed()
        self.script.rollback(self)

    def set_isolation_level(self, level):
        """As per psycopg1 extension."""
        self._checkClosed()
        self.script.set_isolation_level(self, level)

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
    """A fake DB-API cursor as produced by MockDbConnection.cursor.
    
    The real work is done by the associated ScriptRecorder or ScriptPlayer
    using the common interface, making this class independent on what
    mode the mock database is running in.
    """
    # The ExecuteScriptEntry for the in progress query, if there is one.
    # It stores any unfetched results and cursor metadata such as the
    # resultset description.
    _script_entry = None

    arraysize = 100 # As per DB-API.
    connection = None # As per DB-API optional extension.
    real_cursor = None # The real cursor if there is one.

    def __init__(self, connection, real_cursor=None):
        self.connection = connection
        self.real_cursor = real_cursor

    @property
    def description(self):
        """As per DB-API, pulled from the script entry."""
        if self._script_entry is None:
            return None
        return self._script_entry.description

    @property
    def rowcount(self):
        """Return the rowcount only if all the results have been consumed.

        As per DB-API, pulled from the script entry.
        """
        if not isinstance(self._script_entry, ExecuteScriptEntry):
            return -1

        results = self._script_entry.results

        if results is None: # DELETE or UPDATE set rowcount.
            return self._script_entry.rowcount
        
        if results is None or self._fetch_position < len(results):
            return -1
        return self._script_entry.rowcount

    _closed = False

    def close(self):
        """As per DB-API."""
        self._checkClosed()
        self._closed = True
        if self.real_cursor is not None:
            self.real_cursor.close()
            self.real_cursor = None
            self.connection = None

    def _checkClosed(self):
        """Raise an exception if the cursor or connection is closed."""
        if self._closed is True:
            raise psycopg2.Error('Cursor closed.')
        self.connection._checkClosed()

    # Index in our results that the next fetch will return. We don't consume
    # the results list: if we are recording we need to keep the results 
    # so we can serialize at the end of the test.
    _fetch_position = 0

    def execute(self, query, parameters=None):
        """As per DB-API."""
        self._checkClosed()
        self._script_entry = self.connection.script.execute(
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
        if self._script_entry is None:
            raise psycopg2.Error("No query issued yet")
        if self._script_entry.results is None:
            raise psycopg2.Error("Query returned no results")
        try:
            row = self._script_entry.results[self._fetch_position]
            self._fetch_position += 1
            return row
        except IndexError:
            return None

    def fetchmany(self, size=None):
        """As per DB-API."""
        self._checkClosed()
        raise NotImplementedError('fetchmany')

    def fetchall(self):
        """As per DB-API."""
        self._checkClosed()
        if self._script_entry is None:
            raise psycopg2.Error('No query issued yet')
        if self._script_entry.results is None:
            raise psycopg2.Error('Query returned no results')
        results = self._script_entry.results[self._fetch_position:]
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
    ##         raise StopIteration
    ##     else:
    ##         return row

    ## def __iter__(self):
    ##     """As per iterator spec and DB-API optional extension."""
    ##     return self

