# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# We use global in this module.
# pylint: disable-msg=W0602

__metaclass__ = type

import datetime
import os
import re
import sys
import thread
import threading
from time import time
import traceback
import warnings

import psycopg2
from psycopg2.extensions import (
    ISOLATION_LEVEL_AUTOCOMMIT,
    ISOLATION_LEVEL_READ_COMMITTED,
    ISOLATION_LEVEL_SERIALIZABLE,
    QueryCanceledError,
    )
import pytz
from storm.database import register_scheme
from storm.databases.postgres import (
    Postgres,
    PostgresConnection,
    PostgresTimeoutTracer,
    )
from storm.exceptions import TimeoutError
from storm.store import Store
from storm.tracer import install_tracer
from storm.zope.interfaces import IZStorm
import transaction
from zope.component import getUtility
from zope.interface import (
    alsoProvides,
    classImplements,
    classProvides,
    implements,
    )
from zope.security.proxy import removeSecurityProxy

from canonical.config import (
    config,
    DatabaseConfig,
    dbconfig,
    )
from canonical.database.interfaces import IRequestExpired
from canonical.launchpad.interfaces import (
    IMasterObject,
    IMasterStore,
    )
from canonical.launchpad.readonly import is_read_only
from canonical.launchpad.webapp.dbpolicy import MasterDatabasePolicy
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    MASTER_FLAVOR,
    ReadOnlyModeViolation,
    SLAVE_FLAVOR,
    )
from canonical.launchpad.webapp.opstats import OpStats
from canonical.lazr.utils import get_current_browser_request, safe_hasattr
from lp.services.timeline.timeline import Timeline
from lp.services.timeline.requesttimeline import (
    get_request_timeline,
    set_request_timeline,
    )


__all__ = [
    'RequestExpired',
    'set_request_started',
    'clear_request_started',
    'get_request_statements',
    'get_request_start_time',
    'get_request_duration',
    'get_store_name',
    'hard_timeout_expired',
    'soft_timeout_expired',
    'StoreSelector',
    ]


UTC = pytz.utc

classImplements(TimeoutError, IRequestExpired)


class LaunchpadTimeoutError(TimeoutError):
    """A variant of TimeoutError that reports the original PostgreSQL error.
    """

    def __init__(self, statement, params, original_error):
        super(LaunchpadTimeoutError, self).__init__(statement, params)
        self.original_error = original_error

    def __str__(self):
        return ('Statement: %r\nParameters:%r\nOriginal error: %r'
                % (self.statement, self.params, self.original_error))

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


_local = threading.local()


class CommitLogger:
    def __init__(self, txn):
        self.txn = txn

    def newTransaction(self, txn):
        pass

    def beforeCompletion(self, txn):
        pass

    def afterCompletion(self, txn):
        action = get_request_timeline(get_current_browser_request()).start(
            "SQL-nostore", 'Transaction completed, status: %s' % txn.status)
        action.finish()


def set_request_started(
    starttime=None, request_statements=None, txn=None, enable_timeout=True):
    """Set the start time for the request being served by the current
    thread.

    :param start_time: The start time of the request. If given, it is used as
        the start time for the request, as returned by time().  If it is not
        given, the current time is used.
    :param request_statements; The sequence used to store the logged SQL
        statements.
    :type request_statements: mutable sequence.
    :param txn: The current transaction manager. If given, txn.commit() and
        txn.abort() calls are logged too.
    :param enable_timeout: If True, a timeout error is raised if the request
        runs for a longer time than the configured timeout.
    """
    if getattr(_local, 'request_start_time', None) is not None:
        warnings.warn('set_request_started() called before previous request '
                      'finished', stacklevel=1)

    if starttime is None:
        starttime = time()
    _local.request_start_time = starttime
    if request_statements is not None:
        # Requires poking at the API; default is to Just Work.
        request = get_current_browser_request()
        set_request_timeline(request, Timeline(request_statements))
    _local.current_statement_timeout = None
    _local.enable_timeout = enable_timeout
    if txn is not None:
        _local.commit_logger = CommitLogger(txn)
        txn.registerSynch(_local.commit_logger)

def clear_request_started():
    """Clear the request timer.  This function should be called when
    the request completes.
    """
    if getattr(_local, 'request_start_time', None) is None:
        warnings.warn('clear_request_started() called outside of a request')
    _local.request_start_time = None
    request = get_current_browser_request()
    set_request_timeline(request, Timeline())
    commit_logger = getattr(_local, 'commit_logger', None)
    if commit_logger is not None:
        _local.commit_logger.txn.unregisterSynch(_local.commit_logger)
        del _local.commit_logger


def summarize_requests():
    """Produce human-readable summary of requests issued so far."""
    secs = get_request_duration()
    request = get_current_browser_request()
    timeline = get_request_timeline(request)
    from canonical.launchpad.webapp.errorlog import (
        maybe_record_user_requested_oops)
    oopsid = maybe_record_user_requested_oops()
    if oopsid is None:
        oops_str = ""
    else:
        oops_str = " %s" % oopsid
    log = "%s queries/external actions issued in %.2f seconds%s" % (
        len(timeline.actions), secs, oops_str)
    return log


def store_sql_statements_and_request_duration(event):
    actions = get_request_timeline(get_current_browser_request()).actions
    event.request.setInWSGIEnvironment(
        'launchpad.nonpythonstatements', len(actions))
    event.request.setInWSGIEnvironment(
        'launchpad.requestduration', get_request_duration())


def get_request_statements():
    """Get the list of executed statements in the request.

    The list is composed of (starttime, endtime, db_id, statement) tuples.
    Times are given in milliseconds since the start of the request.
    """
    result = []
    request = get_current_browser_request()
    for action in get_request_timeline(request).actions:
        if not action.category.startswith("SQL-"):
            continue
        # Can't show incomplete requests in this API
        if action.duration is None:
            continue
        result.append(action.log_tuple())
    return result


def get_request_start_time():
    """Get the time at which the request started."""
    return getattr(_local, 'request_start_time', None)


def get_request_duration(now=None):
    """Get the duration of the current request in seconds."""
    starttime = getattr(_local, 'request_start_time', None)
    if starttime is None:
        return -1

    if now is None:
        now = time()
    return now - starttime


def _check_expired(timeout):
    """Checks whether the current request has passed the given timeout."""
    if timeout is None or not getattr(_local, 'enable_timeout', True):
        return False # no timeout configured or timeout disabled.

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


class RequestExpired(RuntimeError):
    """Request has timed out."""
    implements(IRequestExpired)


# ---- Prevent database access in the main thread of the app server

class StormAccessFromMainThread(Exception):
    """The main thread must not access the database via Storm.

    Occurs only if the appserver is running. Other code, such as the test
    suite, can do what it likes.
    """

_main_thread_id = None

def break_main_thread_db_access(*ignored):
    """Ensure that Storm connections are not made in the main thread.

    When the app server is running, we want ensure we don't use the
    connection cache from the main thread as this would only be done
    on process startup and would leave an open connection dangling,
    wasting resources.

    This method is invoked by an IProcessStartingEvent - it would be
    easier to do on module load, but the test suite has legitimate uses
    for using connections from the main thread.
    """
    # Record the ID of the main thread.
    # pylint: disable-msg=W0603
    global _main_thread_id
    _main_thread_id = thread.get_ident()

    try:
        getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
    except StormAccessFromMainThread:
        # LaunchpadDatabase correctly refused to create a connection
        pass
    else:
        # We can't specify the order event handlers are called, so
        # this means some other code has used storm before this
        # handler.
        raise StormAccessFromMainThread()


# ---- Storm database classes

isolation_level_map = {
    'autocommit': ISOLATION_LEVEL_AUTOCOMMIT,
    'read_committed': ISOLATION_LEVEL_READ_COMMITTED,
    'serializable': ISOLATION_LEVEL_SERIALIZABLE,
    }


class ReadOnlyModeConnection(PostgresConnection):
    """storm.database.Connection for read-only mode Launchpad."""
    def execute(self, statement, params=None, noresult=False):
        """See storm.database.Connection."""
        try:
            return super(ReadOnlyModeConnection, self).execute(
                statement, params, noresult)
        except psycopg2.InternalError, exception:
            # Error 25006 is 'ERROR:  transaction is read-only'. This
            # is raised when an attempt is made to make changes when
            # the connection has been put in read-only mode.
            if exception.pgcode == '25006':
                raise ReadOnlyModeViolation(None, sys.exc_info()[2])
            raise


class LaunchpadDatabase(Postgres):

    _dsn_user_re = re.compile('user=[^ ]*')

    def __init__(self, uri):
        # The uri is just a property name in the config, such as main_master
        # or main_slave.
        # We don't invoke the superclass constructor as it has a very limited
        # opinion on what uri is.
        # pylint: disable-msg=W0231
        self._uri = uri
        # A unique name for this database connection.
        self.name = uri.database

    @property
    def dsn_without_user(self):
        """This database's dsn without the 'user=...' bit."""
        assert self._dsn is not None, (
            'Must not be called before self._dsn has been set.')
        return self._dsn_user_re.sub('', self._dsn)

    def raw_connect(self):
        # Prevent database connections from the main thread if
        # break_main_thread_db_access() has been run.
        if (_main_thread_id is not None and
            _main_thread_id == thread.get_ident()):
            raise StormAccessFromMainThread()

        try:
            config_section, realm, flavor = self._uri.database.split('-')
        except ValueError:
            raise AssertionError(
                'Connection uri %s does not match section-realm-flavor format'
                % repr(self._uri.database))

        assert realm == 'main', 'Unknown realm %s' % realm
        assert flavor in ('master', 'slave'), 'Unknown flavor %s' % flavor

        my_dbconfig = DatabaseConfig()
        my_dbconfig.setConfigSection(config_section)

        # We set self._dsn here rather than in __init__ so when the Store
        # is reconnected it pays attention to any config changes.
        config_entry = '%s_%s' % (realm, flavor)
        connection_string = getattr(my_dbconfig, config_entry)
        assert 'user=' not in connection_string, (
                "Database username should not be specified in "
                "connection string (%s)." % connection_string)

        # Try to lookup dbuser using the $realm_dbuser key. If this fails,
        # fallback to the dbuser key.
        dbuser = getattr(my_dbconfig, '%s_dbuser' % realm, my_dbconfig.dbuser)

        self._dsn = "%s user=%s" % (connection_string, dbuser)

        flags = _get_dirty_commit_flags()

        if my_dbconfig.isolation_level is None:
            self._isolation = ISOLATION_LEVEL_SERIALIZABLE
        else:
            self._isolation = isolation_level_map[my_dbconfig.isolation_level]

        raw_connection = super(LaunchpadDatabase, self).raw_connect()

        # Set read only mode for the session.
        # An alternative would be to use the _ro users generated by
        # security.py, but this would needlessly double the number
        # of database users we need to maintain ACLs for on production.
        if flavor == SLAVE_FLAVOR:
            raw_connection.cursor().execute(
                'SET DEFAULT_TRANSACTION_READ_ONLY TO TRUE')
            # Make the altered session setting stick.
            raw_connection.commit()
        else:
            assert config_entry.endswith('_master'), (
                'DB connection URL %s does not meet naming convention.')

        _reset_dirty_commit_flags(*flags)
        return raw_connection

    @property
    def connection_factory(self):
        """Return the correct connection factory for the current mode.

        If we are running in read-only mode, returns a
        ReadOnlyModeConnection. Otherwise it returns the Storm default.
        """
        if is_read_only():
            return ReadOnlyModeConnection
        return super(LaunchpadDatabase, self).connection_factory


class LaunchpadSessionDatabase(Postgres):

    # A unique name for this database connection.
    name = 'session'

    def raw_connect(self):
        self._dsn = 'dbname=%s user=%s' % (config.launchpad_session.dbname,
                                           config.launchpad_session.dbuser)
        if config.launchpad_session.dbhost:
            self._dsn += ' host=%s' % config.launchpad_session.dbhost

        flags = _get_dirty_commit_flags()
        raw_connection = super(LaunchpadSessionDatabase, self).raw_connect()
        if safe_hasattr(raw_connection, 'auto_close'):
            raw_connection.auto_close = False
        raw_connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        _reset_dirty_commit_flags(*flags)
        return raw_connection


register_scheme('launchpad', LaunchpadDatabase)
register_scheme('launchpad-session', LaunchpadSessionDatabase)


class LaunchpadTimeoutTracer(PostgresTimeoutTracer):
    """Storm tracer class to keep statement execution time bounded."""

    def __init__(self):
        # pylint: disable-msg=W0231
        # The parent class __init__ just sets the granularity
        # attribute, which we are handling with a property.
        pass

    @property
    def granularity(self):
        return dbconfig.db_statement_timeout_precision / 1000.0

    def connection_raw_execute(self, connection, raw_cursor,
                               statement, params):
        """See `TimeoutTracer`"""
        # Only perform timeout handling on LaunchpadDatabase
        # connections.
        if not isinstance(connection._database, LaunchpadDatabase):
            return
        # If we are outside of a request, don't do timeout adjustment.
        if self.get_remaining_time() is None:
            return
        try:
            super(LaunchpadTimeoutTracer, self).connection_raw_execute(
                connection, raw_cursor, statement, params)
        except TimeoutError:
            info = sys.exc_info()
            transaction.doom()
            OpStats.stats['timeouts'] += 1
            try:
                raise info[0], info[1], info[2]
            finally:
                info = None

    def connection_raw_execute_error(self, connection, raw_cursor,
                                     statement, params, error):
        """See `TimeoutTracer`"""
        # Only perform timeout handling on LaunchpadDatabase
        # connections.
        if not isinstance(connection._database, LaunchpadDatabase):
            return
        if isinstance(error, QueryCanceledError):
            OpStats.stats['timeouts'] += 1
            raise LaunchpadTimeoutError(statement, params, error)

    def get_remaining_time(self):
        """See `TimeoutTracer`"""
        if (not dbconfig.db_statement_timeout or
            not getattr(_local, 'enable_timeout', True)):
            return None
        start_time = getattr(_local, 'request_start_time', None)
        if start_time is None:
            return None
        now = time()
        ellapsed = now - start_time
        return  dbconfig.db_statement_timeout / 1000.0 - ellapsed


class LaunchpadStatementTracer:
    """Storm tracer class to log executed statements."""

    def __init__(self):
        self._debug_sql = bool(os.environ.get('LP_DEBUG_SQL'))
        self._debug_sql_extra = bool(os.environ.get('LP_DEBUG_SQL_EXTRA'))

    def connection_raw_execute(self, connection, raw_cursor,
                               statement, params):
        if self._debug_sql_extra:
            traceback.print_stack()
            sys.stderr.write("." * 70 + "\n")
        if self._debug_sql or self._debug_sql_extra:
            sys.stderr.write(statement + "\n")
            sys.stderr.write("-" * 70 + "\n")
        # store the last executed statement as an attribute on the current
        # thread
        threading.currentThread().lp_last_sql_statement = statement
        request_starttime = getattr(_local, 'request_start_time', None)
        if request_starttime is None:
            return
        action = get_request_timeline(get_current_browser_request()).start(
            'SQL-%s' % connection._database.name, statement)
        connection._lp_statement_action = action

    def connection_raw_execute_success(self, connection, raw_cursor,
                                       statement, params):
        action = getattr(connection, '_lp_statement_action', None)
        if action is not None:
            # action may be None if the tracer was installed  the statement was
            # submitted.
            action.finish()

    def connection_raw_execute_error(self, connection, raw_cursor,
                                     statement, params, error):
        # Since we are just logging durations, we execute the same
        # hook code for errors as successes.
        self.connection_raw_execute_success(
            connection, raw_cursor, statement, params)


# The LaunchpadTimeoutTracer needs to be installed last, as it raises
# TimeoutError exceptions. When this happens, tracers installed later
# are not invoked.
install_tracer(LaunchpadStatementTracer())
install_tracer(LaunchpadTimeoutTracer())


class StoreSelector:
    """See `canonical.launchpad.webapp.interfaces.IStoreSelector`."""
    classProvides(IStoreSelector)

    @staticmethod
    def push(db_policy):
        """See `IStoreSelector`."""
        if not safe_hasattr(_local, 'db_policies'):
            _local.db_policies = []
        db_policy.install()
        _local.db_policies.append(db_policy)

    @staticmethod
    def pop():
        """See `IStoreSelector`."""
        db_policy = _local.db_policies.pop()
        db_policy.uninstall()
        return db_policy

    @staticmethod
    def get_current():
        """See `IStoreSelector`."""
        try:
            return _local.db_policies[-1]
        except (AttributeError, IndexError):
            return None

    @staticmethod
    def get(name, flavor):
        """See `IStoreSelector`."""
        db_policy = StoreSelector.get_current()
        if db_policy is None:
            db_policy = MasterDatabasePolicy(None)
        return db_policy.getStore(name, flavor)


# We want to be able to adapt a Storm class to an IStore, IMasterStore or
# ISlaveStore. Unfortunately, the component architecture provides no
# way for us to declare that a class, and all its subclasses, provides
# a given interface. This means we need to use an global adapter.

def get_store(storm_class, flavor=DEFAULT_FLAVOR):
    """Return a flavored Store for the given database class."""
    table = getattr(removeSecurityProxy(storm_class), '__storm_table__', None)
    if table is not None:
        return getUtility(IStoreSelector).get(MAIN_STORE, flavor)
    else:
        return None


def get_master_store(storm_class):
    """Return the master Store for the given database class."""
    return get_store(storm_class, MASTER_FLAVOR)


def get_slave_store(storm_class):
    """Return the master Store for the given database class."""
    return get_store(storm_class, SLAVE_FLAVOR)


def get_object_from_master_store(obj):
    """Return a copy of the given object retrieved from its master Store.

    Returns the object if it already comes from the relevant master Store.

    Registered as a trusted adapter, so if the input is security wrapped,
    so is the result. Otherwise an unwrapped object is returned.
    """
    master_store = IMasterStore(obj)
    if master_store is not Store.of(obj):
        obj = master_store.get(obj.__class__, obj.id)
        if obj is None:
            return None
    alsoProvides(obj, IMasterObject)
    return obj


def get_store_name(store):
    """Helper to retrieve the store name for a ZStorm Store."""
    return getUtility(IZStorm).get_name(store)
