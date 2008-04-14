# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
# We use global in this module.
# pylint: disable-msg=W0602

__metaclass__ = type

import os
import sys
import thread
import threading
import traceback
from time import time
import warnings

from zope.component import getUtility
from zope.interface import implements
from zope.rdb.interfaces import DatabaseException
from zope.publisher.interfaces import Retry

from psycopgda.adapter import PsycopgAdapter, PsycopgConnection
import psycopg

import sqlos.connection
from sqlos.interfaces import IConnectionName

from canonical.config import config
from canonical.database.interfaces import IRequestExpired
from canonical.database.sqlbase import cursor, ISOLATION_LEVEL_AUTOCOMMIT
from canonical.launchpad.webapp.interfaces import ILaunchpadDatabaseAdapter
from canonical.launchpad.webapp.opstats import OpStats

__all__ = [
    'DisconnectionError',
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
    # XXX: James Henstridge 2007-05-14:
    # This function needs to check exception messages in order to do
    # its job.  Hopefully we can clean this up when switching to
    # psycopg2, since it exposes the Postgres error codes through its
    # exceptions.
    if isinstance(msg, basestring):
        if (msg.startswith('server closed the connection unexpectedly') or
            msg.startswith('could not connect to server') or
            msg.startswith('no connection to the server')):
            return True
    elif isinstance(msg, dict):
        # Some errors from the connection have a cursor => message
        # dictionary as a value.
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


class DisconnectionError(Exception):
    """Attempt was made to access the database after a disconnection."""


class ReconnectingConnection:
    """A Python DB-API connection class that handles disconnects."""

    _connection = None
    _is_dead = False
    _generation = 0

    def __init__(self, connection_factory):
        self._connection_factory = connection_factory
        self._ensureConnected()

    def _ensureConnected(self):
        """Ensure that we are connected to the database.

        If the connection is marked as dead, or if we can't reconnect,
        then raise DisconnectionError.

        If we need to reconnect, the connection generation number is
        incremented.
        """
        if self._is_dead:
            raise DisconnectionError('Already disconnected')
        if self._connection is not None:
            return
        try:
            self._connection = self._connection_factory()
            self._generation += 1
        except psycopg.OperationalError, exc:
            self._handleDisconnection(exc)

    def _handleDisconnection(self, exc):
        """Note that we were disconnected from the database.

        This resets the internal _connection attribute, and marks the
        connection as dead.  Further attempts to use this connection
        before a rollback() will not result in reconnection.

        This function should be called from an exception handler.
        """
        self._is_dead = True
        self._connection = None
        raise DisconnectionError(str(exc))

    def _checkDisconnect(self, _function, *args, **kwargs):
        """Call a function, checking for database disconnections."""
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
                self._handleDisconnection(exc)
            else:
                raise

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        self._ensureConnected()
        return getattr(self._connection, name)

    def commit(self):
        self._ensureConnected()
        self._checkDisconnect(self._connection.commit)

    def rollback(self):
        """Rollback the database connection.

        If this results in a disconnection error, we ignore it and set
        the connection to None so it gets reconnected next time.
        """
        if self._connection is not None:
            try:
                self._connection.rollback()
            except psycopg.Error, exc:
                if exc.args and _wasDisconnected(exc.args[0]):
                    self._connection = None
                else:
                    raise
        self._is_dead = False

    def cursor(self):
        return ReconnectingCursor(self)


def _handle_disconnections(function_name):
    """Helper routine for generating wrappers that check for disconnection."""
    def func(self, *args, **kwargs):
        self._ensureCursor()
        return self.connection._checkDisconnect(
            getattr(self._cursor, function_name), *args, **kwargs)
    func.__name__ = function_name
    return func


class ReconnectingCursor:
    """A Python DB-API cursor class that handles disconnects."""

    _generation = None
    _cursor = None

    def __init__(self, connection):
        self.connection = connection
        self._ensureCursor()

    def _ensureCursor(self):
        self.connection._ensureConnected()
        # If the cursor and connection generation numbers do not
        # match, then our cursor belongs to a previous (disconnected)
        # connection.
        if self._generation != self.connection._generation:
            self._cursor = None
        if self._cursor is None:
            self._cursor = self.connection._checkDisconnect(
                self.connection._connection.cursor)
            self._generation = self.connection._generation

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        self._ensureCursor()
        return getattr(self._cursor, name)

    execute = _handle_disconnections('execute')
    executemany = _handle_disconnections('executemany')
    fetchone = _handle_disconnections('fetchone')
    fetchmany = _handle_disconnections('fetchmany')
    fetchall = _handle_disconnections('fetchall')


class ReconnectingPsycopgConnection(PsycopgConnection):
    """A PsycopgConnection subclass that joins the Zope transaction
    when cursor() is called.
    """

    def cursor(self):
        """See IZopeConnection"""
        self.registerForTxn()
        return super(ReconnectingPsycopgConnection, self).cursor()


class ReconnectingDatabaseAdapter(PsycopgAdapter):
    """A Postgres database adapter that can reconnect to the database."""

    Connection = ReconnectingConnection

    def connect(self):
        if not self.isConnected():
            try:
                self._v_connection = ReconnectingPsycopgConnection(
                    self.Connection(self._connection_factory), self)
            except psycopg.Error, error:
                raise DatabaseException(str(error))


# ---- Session database adapter

class SessionDatabaseAdapter(ReconnectingDatabaseAdapter):
    """A subclass of ReconnectionDatabaseAdapter that stores its
    connection information in the central launchpad configuration.
    """

    def __init__(self, dsn=None):
        """Ignore dsn"""
        super(SessionDatabaseAdapter, self).__init__(
            'dbi://%(dbuser)s:@%(dbhost)s/%(dbname)s' % dict(
                dbuser=config.launchpad_session.dbuser,
                dbhost=config.launchpad_session.dbhost or '',
                dbname=config.launchpad_session.dbname))

    def _connection_factory(self):
        flags = _get_dirty_commit_flags()
        connection = super(SessionDatabaseAdapter, self)._connection_factory()
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        connection.cursor().execute("SET client_encoding TO UTF8")
        _reset_dirty_commit_flags(*flags)
        return connection


_local = threading.local()


# ---- Main Launchpad database adapter

def set_request_started(starttime=None):
    """Set the start time for the request being served by the current
    thread.

    If the argument is given, it is used as the start time for the
    request, as returned by time().  If it is not given, the
    current time is used.
    """
    if getattr(_local, 'request_start_time', None) is not None:
        warnings.warn('set_request_started() called before previous request '
                      'finished', stacklevel=1)

    if starttime is None:
        starttime = time()
    _local.request_start_time = starttime
    _local.request_statements = []
    _local.current_statement_timeout = None


def clear_request_started():
    """Clear the request timer.  This function should be called when
    the request completes.
    """
    if getattr(_local, 'request_start_time', None) is None:
        warnings.warn('clear_request_started() called outside of a request')

    _local.request_start_time = None
    _local.request_statements = []


def summarize_requests():
    """Produce human-readable summary of requests issued so far."""
    secs = get_request_duration()
    statements = getattr(_local, 'request_statements', [])
    log = "%s queries issued in %.2f seconds" % (len(statements), secs)
    return log


def store_sql_statements_and_request_duration(event):
    event.request.setInWSGIEnvironment(
        'launchpad.sqlstatements', len(get_request_statements()))
    event.request.setInWSGIEnvironment(
        'launchpad.requestduration', get_request_duration())


def get_request_statements():
    """Get the list of executed statements in the request.

    The list is composed of (starttime, endtime, statement) tuples.
    Times are given in milliseconds since the start of the request.
    """
    return getattr(_local, 'request_statements', [])


def get_request_duration(now=None):
    """Get the duration of the current request in seconds."""
    starttime = getattr(_local, 'request_start_time', None)
    if starttime is None:
        return -1

    if now is None:
        now = time()
    return now - starttime


def _log_statement(starttime, endtime, connection_wrapper, statement):
    """Log that a database statement was executed."""
    request_starttime = getattr(_local, 'request_start_time', None)
    if request_starttime is None:
        return

    # convert times to integer millisecond values
    starttime = int((starttime - request_starttime) * 1000)
    endtime = int((endtime - request_starttime) * 1000)
    _local.request_statements.append((starttime, endtime, statement))

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

    requesttime = (time() - starttime) * 1000
    return requesttime > timeout


def hard_timeout_expired():
    """Returns True if the hard request timeout been reached."""
    return _check_expired(config.database.db_statement_timeout)


def soft_timeout_expired():
    """Returns True if the soft request timeout been reached."""
    return _check_expired(config.database.soft_request_timeout)


def reset_hard_timeout(execute_func):
    """Reset the statement_timeout to remaining wallclock time."""
    timeout = config.database.db_statement_timeout
    if timeout is None:
        return # No timeout - nothing to do

    global _local

    start_time = getattr(_local, 'request_start_time', None)
    if start_time is None:
        return # Not in a request - nothing to do

    now = time()
    remaining_ms = (timeout - int((now - start_time) * 1000))

    if remaining_ms <= 0:
        return # Already timed out - nothing to do

    # Only reset the statement timeout once in this many milliseconds
    # to avoid too many database round trips.
    precision = config.database.db_statement_timeout_precision

    current_statement_timeout = getattr(
            _local, 'current_statement_timeout', None)
    if (current_statement_timeout is None
            or current_statement_timeout - remaining_ms > precision):
        execute_func("SET statement_timeout TO %d" % remaining_ms)
        _local.current_statement_timeout = remaining_ms


class RequestExpired(RuntimeError):
    """Request has timed out."""
    implements(IRequestExpired)


class RequestStatementTimedOut(RequestExpired):
    """A statement that was part of a request timed out."""


class LaunchpadConnection(ReconnectingConnection):
    """A simple wrapper around a DB-API connection object.

    Overrides the cursor() method to return LaunchpadCursor objects.
    """

    def cursor(self):
        return LaunchpadCursor(self)

    def commit(self):
        starttime = time()
        try:
            super(LaunchpadConnection, self).commit()
        finally:
            _log_statement(starttime, time(), self, 'COMMIT')

    def rollback(self):
        starttime = time()
        try:
            super(LaunchpadConnection, self).rollback()
        finally:
            _log_statement(starttime, time(), self, 'ROLLBACK')


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

        reset_hard_timeout(super(LaunchpadCursor, self).execute)

        try:
            starttime = time()
            if os.environ.get("LP_DEBUG_SQL_EXTRA"):
                traceback.print_stack()
                sys.stderr.write("." * 70 + "\n")
            if (os.environ.get("LP_DEBUG_SQL_EXTRA") or
                os.environ.get("LP_DEBUG_SQL")):
                sys.stderr.write(statement + "\n")
                sys.stderr.write("-" * 70 + "\n")
            try:
                return super(LaunchpadCursor, self).execute(
                        statement, *args, **kwargs)
            finally:
                _log_statement(
                        starttime, time(),
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
    """A subclass of ReconnectingDatabaseAdapter that performs some
    additional connection setup.
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
        self.setDSN('dbi://%s@%s/%s' % (
            self.getUser(),
            config.database.dbhost or '',
            config.database.dbname
            ))

        flags = _get_dirty_commit_flags()
        connection = super(LaunchpadDatabaseAdapter,
                           self)._connection_factory()

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

    def getUser(self):
        """Return the dbuser used by this connection."""
        return getattr(self._local, 'dbuser', None) or config.launchpad.dbuser


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


