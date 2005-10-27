# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import threading
import time
import warnings

from zope.interface import implements
from zope.app.rdb import ZopeConnection

from psycopgda.adapter import PsycopgAdapter
import psycopg

from canonical.config import config
from canonical.database.interfaces import IRequestExpired
from canonical.database.sqlbase import connect
from canonical.launchpad.webapp.interfaces import ILaunchpadDatabaseAdapter

__all__ = [
    'LaunchpadDatabaseAdapter',
    'RequestExpired',
    'set_request_started',
    'clear_request_started',
    ]


class LaunchpadDatabaseAdapter(PsycopgAdapter):
    """A subclass of PsycopgAdapter that performs some additional
    connection setup.
    """
    implements(ILaunchpadDatabaseAdapter)

    def __init__(self, dsn=None):
        """Ignore dsn"""
        super(LaunchpadDatabaseAdapter, self).__init__('dbi://')

    def connect(self, _dbuser=None):
        """See zope.app.rdb.interfaces.IZopeDatabaseAdapter

        We pass the database user through to avoid having to keep state
        using a thread local.
        """
        if not self.isConnected():
            try:
                self._v_connection = ZopeConnection(
                    self._connection_factory(_dbuser=_dbuser), self)
            # Note: I added the general Exception, since the DA can return
            # implementation-specific errors. But we really want to catch all
            # issues at this point, so that we can convert it to a
            # DatabaseException.
            except psycopg.Error, error:
                raise DatabaseException, str(error)

    def _connection_factory(self, _dbuser=None):
        """Override method provided by PsycopgAdapter to pull
        connection settings from the config file
        """
        self._registerTypes()
        if _dbuser is None:
            _dbuser = config.launchpad.dbuser
        connection = connect(_dbuser, config.dbname)

        if config.launchpad.db_statement_timeout is not None:
            cursor = connection.cursor()
            cursor.execute('SET statement_timeout TO %d' %
                           config.launchpad.db_statement_timeout)
            connection.commit()

        return ConnectionWrapper(connection)

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
        self.connect(_dbuser=dbuser)


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


def clear_request_started():
    """Clear the request timer.  This function should be called when
    the request completes.
    """
    if getattr(_local, 'request_start_time', None) is None:
        warnings.warn('clear_request_started() called outside of a request')

    _local.request_start_time = None


def _request_expired():
    """Checks whether the current request has expired."""
    if config.launchpad.db_statement_timeout is None:
        return False # no timeout configured

    starttime = getattr(_local, 'request_start_time', None)
    if starttime is None:
        return False # no current request

    requesttime = (time.time() - starttime) * 1000
    return requesttime > config.launchpad.db_statement_timeout


class RequestExpired(RuntimeError):
    """Request has timed out."""
    implements(IRequestExpired)


class RequestQueryTimedOut(RequestExpired):
    """A query that was part of a request timed out."""


class ConnectionWrapper:
    """A simple wrapper around a DB-API connection object.

    Overrides the cursor() method to return CursorWrapper objects.
    """
    
    def __init__(self, connection):
        self.__dict__['_conn'] = connection

    def cursor(self):
        return CursorWrapper(self._conn.cursor())

    def __getattr__(self, attr):
        return getattr(self._conn, attr)

    def __setattr__(self, attr, value):
        setattr(self._conn, attr, value)


class CursorWrapper:
    """A simple wrapper for a DB-API cursor object.

    Overrides the execute() method to check whether the current
    request has expired.
    """

    def __init__(self, cursor):
        self.__dict__['_cur'] = cursor

    def execute(self, *args, **kwargs):
        """Execute an SQL query, provided that the current request hasn't
        timed out.

        If the request has timed out, the current transaction will be
        doomed (but not completed -- further queries will fail til the
        transaction completes) and the RequestExpired exception will
        be raised.
        """
        if _request_expired():
            # make sure the current transaction can not be committed by
            # sending a broken SQL statement to the database
            try:
                self._cur.execute('break this transaction')
            except psycopg.DatabaseError:
                pass
            raise RequestExpired(args, kwargs)
        try:
            return self._cur.execute(*args, **kwargs)
        except psycopg.ProgrammingError, error:
            if len(error.args):
                errorstr = error.args[0]
                if errorstr.startswith(
                    'ERROR:  canceling query due to user request'):
                    raise RequestQueryTimedOut(args, kwargs, errorstr)
            raise

    def __getattr__(self, attr):
        return getattr(self._cur, attr)

    def __setattr__(self, attr, value):
        setattr(self._cur, attr, value)
