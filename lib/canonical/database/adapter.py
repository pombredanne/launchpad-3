# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import threading
import time

from psycopgda.adapter import PsycopgAdapter

from canonical.config import config

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

    def _connection_factory(self):
        connection = PsycopgAdapter._connection_factory(self)

        if config.launchpad.db_statement_timeout is not None:
            cursor = connection.cursor()
            cursor.execute('SET statement_timeout TO %d' %
                           config.launchpad.db_statement_timeout)
            connection.commit()

        return ConnectionWrapper(connection)


_local = threading.local()

def set_request_started(starttime=None):
    '''Set the start time for the request being served by the current
    thread.

    If the argument is given, it is used as the start time for the
    request, as returned by time.time().  If it is not given, the
    current time is used.'''
    if starttime is None:
        starttime = time.time()
    _local.request_start_time = starttime

def clear_request_started():
    '''Clear the request timer.  This function should be called when
    the request completes.'''
    _local.request_start_time = None

def _request_expired():
    '''Checks whether the current request has expired.'''
    if config.launchpad.db_statement_timeout is None:
        return False # no timeout configured

    starttime = getattr(_local, 'request_start_time', None)
    if starttime is None:
        return False # no current request

    requesttime = (time.time() - starttime) * 1000
    return requesttime > config.launchpad.db_statement_timeout


class RequestExpired(RuntimeError):
    '''Request has timed out'''


class ConnectionWrapper:
    def __init__(self, connection):
        self.__dict__['_conn'] = connection

    def cursor(self):
        return CursorWrapper(self._conn.cursor())

    def __getattr__(self, attr):
        return getattr(self._conn, attr)

    def __setattr__(self, attr, value):
        setattr(self._conn, attr, value)

class CursorWrapper:
    def __init__(self, cursor):
        self.__dict__['_cur'] = cursor

    def execute(self, *args, **kwargs):
        if _request_expired():
            raise RequestExpired('The current request has expired')
        return self._cur.execute(*args, **kwargs)

    def __getattr__(self, attr):
        return getattr(self._cur, attr)

    def __setattr__(self, attr, value):
        setattr(self._cur, attr, value)
