# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import os
import sys
import thread
import threading
import traceback
import time
import warnings

from zope.component import getUtility
from zope.interface import implements
from zope.app.rdb.interfaces import DatabaseException
from zope.publisher.interfaces import Retry

from psycopgda.adapter import PsycopgAdapter, PsycopgConnection
import psycopg

import sqlos.connection
from sqlos.interfaces import IConnectionName

from canonical.config import config
from canonical.database.interfaces import IRequestExpired
from canonical.database.sqlbase import AUTOCOMMIT_ISOLATION, cursor
from canonical.launchpad.webapp.interfaces import ILaunchpadDatabaseAdapter
from canonical.launchpad.webapp.opstats import OpStats

__all__ = [
    'LaunchpadDatabaseAdapter',
    'SessionDatabaseAdapter',
    'RequestExpired',
    'set_request_started',
    'clear_request_started',
    'get_request_statements',
    'get_request_duration',
    'hard_timeout_expired',
    'soft_timeout_expired',
    ]

def _get_dirty_commit_flags():
    """Return the current dirty commit status"""
    from canonical.ftests.pgsql import ConnectionWrapper
    return (ConnectionWrapper.committed, ConnectionWrapper.dirty)

def _reset_dirty_commit_flags(previous_committed, previous_dirty):
    """Set the dirty commit status to False unless previous is True"""
    from canonical.ftests.pgsql import ConnectionWrapper
    if not previous_committed:
        ConnectionWrapper.committed = False
    if not previous_dirty:
        ConnectionWrapper.dirty = False

# ---- Reconnecting database adapter

def _wasDisconnected(msg):
    """Check if the given exception message indicates a database disconnect.

    The message will either be a string, or a dictionary mapping
    cursors to string messages.
    """
    if isinstance(msg, basestring):
        if (msg.startswith('server closed the connection unexpectedly') or
            msg.startswith('could not connect to server') or
            msg.startswith('no connection to the server')):
            return True
    elif isinstance(msg, dict):
        for value in msg.itervalues():
            if _wasDisconnected(value):
                return True
    return False


class RetryPsycopgIntegrityError(psycopg.IntegrityError, Retry):
    """Act like a psycopg IntegrityError, but also inherit from Retry
       so the Zope3 publishing machinery will retry requests if it is
       raised, as per Bug 31755.
    """
    def __init__(self, exc_info):
        Retry.__init__(self, exc_info)
        integrity_error = exc_info[1]
        psycopg.IntegrityError.__init__(self, *integrity_error.args)


class DisconnectedConnectionError(Exception):
    """Attempt was made to access the database after a disconnection."""


class ReconnectingConnection:
    """A Python DB-API connection class that handles disconnects."""

    _connection = None
    _isDead = False
    _generation = 0

    def __init__(self, connection_factory):
        self._connection_factory = connection_factory
        self._ensureConnected()

    def _ensureConnected(self):
        """Ensure that we are connected to the database.

        If the connection is marked as dead, or if we can't reconnect,
        then raise DisconnectedConnectionError.

        If we need to reconnect, the connection generation number is
        incremented.
        """
        if self._isDead:
            raise Retry((DisconnectedConnectionError,
                         DisconnectedConnectionError('Already disconnected'),
                         None))
        if self._connection is not None:
            return
        try:
            self._connection = self._connection_factory()
        except psycopg.OperationalError:
            self._disconnected()
        self._generation += 1

    def _disconnected(self):
        """Note that we were disconnected from the database.

        This resets the internal _connection attribute, and marks the
        connection as dead.  Further attempts to use this connection
        before a rollback() will not result in reconnection.

        This function should be called from an exception handler.
        """
        self._isDead = True
        self._connection = None
        raise Retry(sys.exc_info())

    def _checkDisconnect(self, _function, *args, **kwargs):
        try:
            return _function(*args, **kwargs)
        except psycopg.IntegrityError:
            # Fix Bug 31755. There are unavoidable race conditions
            # when handling form submissions (unless we require tables
            # to be locked, which would kill performance). To fix
            # this, if we get an IntegrityError from a constraints
            # violation we ask Zope to retry the request. This will be
            # fairly harmless when database constraints are triggered
            # due to insufficient form validation. When the request is
            # retried, the form validation code will again get a
            # chance to detect if database constraints will be
            # violated and display a suitable error message.
            raise RetryPsycopgIntegrityError(sys.exc_info())
        except psycopg.Error, exc:
            if exc.args and _wasDisconnected(exc.args[0]):
                self._disconnected()
            else:
                raise

    def __getattr__(self, name):
        self._ensureConnected()
        return getattr(self._connection, name)

    def commit(self):
        self._ensureConnected()
        self._checkDisconnect(self._connection.commit)

    def rollback(self):
        """Rollback the database connection.

        If this results in a disconnection error, we ignore it and set
        the connection to None so it gets reconnected next time."""
        if self._connection is not None:
            try:
                self._connection.rollback()
            except psycopg.Error, exc:
                if exc.args and _wasDisconnected(exc.args[0]):
                    self._connection = None
                else:
                    raise
        self._isDead = False

    def cursor(self):
        return ReconnectingCursor(self)


class ReconnectingCursor:
    """A Python DB-API cursor class that handles disconnects."""

    _generation = None
    _cursor = None

    def __init__(self, connection):
        self.connection = connection
        self._ensureCursor()

    def _ensureCursor(self):
        self.connection._ensureConnected()
        # if the generation numbers don't match, we have an old cursor
        if self._generation != self.connection._generation:
            self._cursor = None
        if self._cursor is None:
            self._cursor = self.connection._checkDisconnect(
                self.connection._connection.cursor)
            self._generation = self.connection._generation

    def __getattr__(self, name):
        self._ensureCursor()
        return getattr(self._cursor, name)

    def execute(self, *args, **kwargs):
        self._ensureCursor()
        return self.connection._checkDisconnect(
            self._cursor.execute, *args, **kwargs)

    def executemany(self, *args, **kwargs):
        self._ensureCursor()
        return self.connection._checkDisconnect(
            self._cursor.executemany, *args, **kwargs)

    def fetchone(self, *args, **kwargs):
        self._ensureCursor()
        return self.connection._checkDisconnect(
            self._cursor.fetchone, *args, **kwargs)

    def fetchmany(self, *args, **kwargs):
        self._ensureCursor()
        return self.connection._checkDisconnect(
            self._cursor.fetchmany, *args, **kwargs)

    def fetchall(self, *args, **kwargs):
        self._ensureCursor()
        return self.connection._checkDisconnect(
            self._cursor.fetchall, *args, **kwargs)


class ReconnectingDatabaseAdapter(PsycopgAdapter):
    """A Postgres database adapter that can reconnect to the database."""

    Connection = ReconnectingConnection

    def connect(self):
        if not self.isConnected():
            try:
                self._v_connection = PsycopgConnection(
                    self.Connection(self._connection_factory), self)
            except psycopg.Error, error:
                raise DatabaseException, str(error)


class SessionDatabaseAdapter(ReconnectingDatabaseAdapter):
    """A subclass of PsycopgAdapter that stores its connection information
    in the central launchpad configuration
    """
    
    def __init__(self, dsn=None):
        """Ignore dsn"""
        super(SessionDatabaseAdapter, self).__init__(
            'dbi://%(dbuser)s:@%(dbhost)s/%(dbname)s' % dict(
                dbuser=config.launchpad.session.dbuser,
                dbhost=config.launchpad.session.dbhost or '',
                dbname=config.launchpad.session.dbname))

    def _connection_factory(self):
        flags = _get_dirty_commit_flags()
        connection = super(SessionDatabaseAdapter, self)._connection_factory()
        connection.set_isolation_level(AUTOCOMMIT_ISOLATION)
        connection.cursor().execute("SET client_encoding TO UTF8")
        _reset_dirty_commit_flags(*flags)
        return connection


_local = threading.local()


def set_request_started(starttime=None):
    """Set the start time for the request being served by the current
    thread.

    If the argument is given, it is used as the start time for the
    request, as returned by time.time().  If it is not given, the
    current time is used.
    """
    if getattr(_local, 'request_start_time', None) is not None:
        warnings.warn('set_request_started() called before previous request '
                      'finished', stacklevel=1)

    if starttime is None:
        starttime = time.time()
    _local.request_start_time = starttime
    _local.request_statements = []


def clear_request_started():
    """Clear the request timer.  This function should be called when
    the request completes.
    """
    if getattr(_local, 'request_start_time', None) is None:
        warnings.warn('clear_request_started() called outside of a request')

    _local.request_start_time = None
    _local.request_statements = []


def get_request_statements():
    """Get the list of executed statements in the request.

    The list is composed of (starttime, endtime, statement) tuples.
    Times are given in milliseconds since the start of the request.
    """
    return getattr(_local, 'request_statements', [])


def get_request_duration(now=None):
    """Get the duration of the current request in seconds.

    """
    starttime = getattr(_local, 'request_start_time', None)
    if starttime is None:
        return -1

    if now is None:
        now = time.time()
    return now - starttime


def _log_statement(starttime, endtime, connection_wrapper, statement):
    """Log that a database statement was executed."""
    request_starttime = getattr(_local, 'request_start_time', None)
    if request_starttime is None:
        return

    # convert times to integer millisecond values
    starttime = int((starttime - request_starttime) * 1000)
    endtime = int((endtime - request_starttime) * 1000)
    _local.request_statements.append((
        starttime, endtime,
        '/*%s*/ %s' % (id(connection_wrapper), statement)
        ))

    # store the last executed statement as an attribute on the current
    # thread
    threading.currentThread().lp_last_sql_statement = statement


def _check_expired(timeout):
    """Checks whether the current request has passed the given timeout."""
    if timeout is None:
        return False # no timeout configured

    starttime = getattr(_local, 'request_start_time', None)
    if starttime is None:
        return False # no current request

    requesttime = (time.time() - starttime) * 1000
    return requesttime > timeout


def hard_timeout_expired():
    """Returns True if the hard request timeout been reached."""
    return _check_expired(config.launchpad.db_statement_timeout)


def soft_timeout_expired():
    """Returns True if the soft request timeout been reached."""
    return _check_expired(config.launchpad.soft_request_timeout)


class RequestExpired(RuntimeError):
    """Request has timed out."""
    implements(IRequestExpired)


class RequestStatementTimedOut(RequestExpired):
    """A statement that was part of a request timed out."""


class LaunchpadConnection(ReconnectingConnection):
    """A simple wrapper around a DB-API connection object.

    Overrides the cursor() method to return CursorWrapper objects.
    """
    
    def cursor(self):
        return LaunchpadCursor(self)

    def commit(self):
        starttime = time.time()
        try:
            super(LaunchpadConnection, self).commit()
        finally:
            _log_statement(starttime, time.time(), self, 'COMMIT')

    def rollback(self):
        starttime = time.time()
        try:
            super(LaunchpadConnection, self).rollback()
        finally:
            _log_statement(starttime, time.time(), self, 'ROLLBACK')


class LaunchpadCursor(ReconnectingCursor):
    """A simple wrapper for a DB-API cursor object.

    Overrides the execute() method to check whether the current
    request has expired.
    """

    def execute(self, statement, *args, **kwargs):
        """Execute an SQL query, provided that the current request hasn't
        timed out.

        If the request has timed out, the current transaction will be
        doomed (but not completed -- further queries will fail til the
        transaction completes) and the RequestExpired exception will
        be raised.
        """
        if hard_timeout_expired():
            # make sure the current transaction can not be committed by
            # sending a broken SQL statement to the database
            try:
                super(LaunchpadCursor, self).execute('break this transaction')
            except psycopg.DatabaseError:
                pass
            OpStats.stats['timeouts'] += 1
            raise RequestExpired(statement)
        try:
            starttime = time.time()
            if os.environ.get("LP_DEBUG_SQL_EXTRA"):
                sys.stderr.write("-" * 70 + "\n")
                traceback.print_stack()
                sys.stderr.write("." * 70 + "\n")
            if (os.environ.get("LP_DEBUG_SQL_EXTRA") or 
                os.environ.get("LP_DEBUG_SQL")):
                sys.stderr.write(statement + "\n")
            try:
                return super(LaunchpadCursor, self).execute(
                    '/*%s*/ %s' % (id(self.connection), statement),
                    *args, **kwargs)
            finally:
                _log_statement(
                        starttime, time.time(),
                        self.connection, statement
                        )
        except psycopg.ProgrammingError, error:
            if len(error.args):
                errorstr = error.args[0]
                if (errorstr.startswith(
                    'ERROR:  canceling query due to user request') or
                    errorstr.startswith(
                    'ERROR:  canceling statement due to statement timeout') or
                    errorstr.startswith(
                    'ERROR:  cancelling statement due to statement timeout')):
                    raise RequestStatementTimedOut(statement)
            raise


class LaunchpadDatabaseAdapter(ReconnectingDatabaseAdapter):
    """A subclass of PsycopgAdapter that performs some additional
    connection setup.
    """
    implements(ILaunchpadDatabaseAdapter)

    Connection = LaunchpadConnection

    def __init__(self, dsn=None):
        """Ignore dsn"""
        super(LaunchpadDatabaseAdapter, self).__init__('dbi://')
        self._local = threading.local()

    def _connection_factory(self):
        """Override method provided by PsycopgAdapter to pull
        connection settings from the config file
        """
        dbuser = getattr(self._local, 'dbuser', None)
        self.setDSN('dbi://%s@%s/%s' % (
            dbuser or config.launchpad.dbuser,
            config.dbhost or '',
            config.dbname
            ))

        flags = _get_dirty_commit_flags()
        connection = super(LaunchpadDatabaseAdapter,
                           self)._connection_factory()

        if config.launchpad.db_statement_timeout is not None:
            cursor = connection.cursor()
            cursor.execute('SET statement_timeout TO %d' %
                           config.launchpad.db_statement_timeout)
            connection.commit()

        _reset_dirty_commit_flags(*flags)
        return connection

    def readonly(self):
        """See ILaunchpadDatabaseAdapter"""
        cursor = self._v_connection.cursor()
        cursor.execute('SET TRANSACTION READ ONLY')

    def switchUser(self, dbuser=None):
        """See ILaunchpadDatabaseAdapter"""
        # We have to disconnect and reconnect as we may not be running
        # as a user with privileges to issue 'SET SESSION AUTHORIZATION'
        # commands.
        self.disconnect()
        self._local.dbuser = dbuser
        self.connect()


class SQLOSAccessFromMainThread(Exception):
    """The main thread must not access the database via SQLOS.

    Occurs only if the appserver is running. Other code, such as the test
    suite, can do what it likes.
    """


def break_main_thread_db_access(*ignored):
    """Deliberately corrupt the SQLOS connection cache.

    When the app server is running, we want ensure we don't use the
    connection cache from the main thread as this would only be done
    on process startup and would leave an open connection dangling,
    wasting resources.

    This method is invoked by an IProcessStartingEvent - it would be
    easier to do on module load, but the test suite has legitimate uses
    for using connections from the main thread.
    """
    connection_name = getUtility(IConnectionName).name
    tid = thread.get_ident() # This event handler called on the main thread
    key = (tid, connection_name)


    # We can't specify the order event handlers are called, so detect if
    # another event handler has already been naughty.
    if sqlos.connection.connCache.has_key(key):
        raise SQLOSAccessFromMainThread()

    # Break SQLOS from this thread.

    class BrokenConnection:
        def __getattr__(self, key):
            raise SQLOSAccessFromMainThread()
        
    sqlos.connection.connCache[key] = BrokenConnection()

    # And prove it
    try:
        # Calling cursor() will raise an exception.
        dummy = cursor()
    except SQLOSAccessFromMainThread:
        # This exception occured, so the main thread's connection is
        # appropriately broken.
        pass
    else:
        raise AssertionError("Failed to kill main thread SQLOS connection")

