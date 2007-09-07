# Copyright 2004 Canonical Ltd.  All rights reserved.
'''
Test harness for tests needing a PostgreSQL backend.
'''

__metaclass__ = type

import unittest
import os, os.path, sys
import re
import time
from warnings import warn

import psycopg
from zope.app.rdb.interfaces import DatabaseException
from canonical.database.postgresql import resetSequences

def _caller_debug(lvl=1):
    return
    f1 = sys._getframe(lvl)
    f2 = sys._getframe(lvl+2)
    print '%s - %s (%s line %s)' % (
            f1.f_code.co_name,
            f2.f_code.co_name,
            f2.f_globals['__file__'],
            f2.f_lineno,
            )

class ConnectionWrapper(object):
    real_connection = None
    committed = False
    last_execute = None
    dirty = False

    def __init__(self, real_connection):
        self.__dict__['real_connection'] = real_connection
        PgTestSetup.connections.append(self)

    def close(self):
        _caller_debug()
        if self in PgTestSetup.connections:
            PgTestSetup.connections.remove(self)
            self.__dict__['real_connection'].close()

    def rollback(self, InterfaceError=psycopg.InterfaceError):
        # In our test suites, rollback ends up being called twice in some
        # circumstances. Silently ignoring this is probably not correct,
        # but the alternative is wasting further time chasing this
        # and probably refactoring sqlos and/or zope3
        # -- StuartBishop 2005-01-11
        # Need to store InterfaceError cleverly, otherwise it may have been
        # GCed when the world is being destroyed, leading to an odd
        # AttributeError with
        #   except psycopg.InterfaceError:
        # -- SteveAlexander 2005-03-22
        try:
            self.__dict__['real_connection'].rollback()
        except InterfaceError:
            pass

    def commit(self):
        # flag that a connection has had commit called. This allows
        # optimizations by subclasses, since if no commit has been made,
        # dropping and recreating the database might be unnecessary
        try:
            return self.__dict__['real_connection'].commit()
        finally:
            ConnectionWrapper.committed = True

    def cursor(self):
        return CursorWrapper(self.__dict__['real_connection'].cursor())

    def __getattr__(self, key):
        return getattr(self.__dict__['real_connection'], key)

    def __setattr__(self, key, val):
        return setattr(self.__dict__['real_connection'], key, val)


class CursorWrapper:
    """A wrapper around cursor objects.

    Acts like a normal cursor object, except if CursorWrapper.record_sql is set,
    then queries that pass through CursorWrapper.execute will be appended to
    CursorWrapper.last_executed_sql.  This is useful for tests that want to
    ensure that certain SQL is generated.
    """
    real_cursor = None
    last_executed_sql = []
    record_sql = False

    def __init__(self, real_cursor):
        self.__dict__['real_cursor'] = real_cursor

    def execute(self, *args, **kwargs):
        # Detect if DML has been executed. This method isn't perfect,
        # but should be good enough.
        mutating_commands = ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP']
        for command in mutating_commands:
            if command in args[0].upper():
                ConnectionWrapper.dirty = True

        # Record the last query executed.
        if CursorWrapper.record_sql:
            CursorWrapper.last_executed_sql.append(args[0])
        return self.__dict__['real_cursor'].execute(*args, **kwargs)

    def __getattr__(self, key):
        return getattr(self.__dict__['real_cursor'], key)

    def __setattr__(self, key, val):
        return setattr(self.__dict__['real_cursor'], key, val)


_org_connect = None
def fake_connect(*args, **kw):
    global _org_connect
    return ConnectionWrapper(_org_connect(*args, **kw))

def installFakeConnect():
    global _org_connect
    assert _org_connect is None
    _org_connect = psycopg.connect
    psycopg.connect = fake_connect

def uninstallFakeConnect():
    global _org_connect
    assert _org_connect is not None
    psycopg.connect = _org_connect
    _org_connect = None


class PgTestSetup(object):
    connections = [] # Shared

    template = 'template1'
    dbname = 'launchpad_ftest'
    dbuser = None
    host = None
    port = None

    # (template, name) of last test. Class attribute.
    _last_db = (None, None)
    # Class attribute. True if we should destroy the DB because changes made.
    _reset_db = True

    def __init__(self, template=None, dbname=None, dbuser=None,
            host=None, port=None):
        '''Construct the PgTestSetup

        Note that dbuser is not used for setting up or tearing down
        the database - it is only used by the connect() method
        '''
        if template is not None:
            self.template = template
        if dbname is not None:
            self.dbname = dbname
        if dbuser is not None:
            self.dbuser = dbuser
        if host is not None:
            self.host = host
        if port is not None:
            self.port = port

    def _connectionString(self, dbname, dbuser=None):
        connection_parameters = ['dbname=%s' % dbname]
        if dbuser is not None:
            connection_parameters.append('user=%s' % dbuser)
        if self.host is not None:
            connection_parameters.append('host=%s' % self.host)
        if self.port is not None:
            connection_parameters.append('port=%s' % self.host)
        return ' '.join(connection_parameters)

    def setUp(self):
        '''Create a fresh database (dropping the old if necessary)

        Skips db creation if reset_db is False
        '''
        # This is now done globally in test.py
        #installFakeConnect()
        if (self.template, self.dbname) != PgTestSetup._last_db:
            PgTestSetup._reset_db = True
        if not PgTestSetup._reset_db:
            # The database doesn't need to be reset. We reset the sequences
            # anyway (because they might have been incremented even if
            # nothing was committed), making sure not to disturb the
            # 'committed' flag, and we're done.
            con = psycopg.connect(self._connectionString(self.dbname))
            cur = con.cursor()
            resetSequences(cur)
            con.commit()
            con.close()
            ConnectionWrapper.committed = False
            ConnectionWrapper.dirty = False
            return
        self.dropDb()

        # Create the database from the template. We might need to keep
        # trying for a few seconds in case there are connections to the
        # template database that are slow in dropping off.
        con = psycopg.connect(self._connectionString(self.template))
        try:
            con.set_isolation_level(0)
            cur = con.cursor()
            attempts = 60
            for counter in range(0, attempts):
                try:
                    cur.execute(
                        "CREATE DATABASE %s TEMPLATE=%s ENCODING='UNICODE'" % (
                            self.dbname, self.template))
                    break
                except psycopg.ProgrammingError, x:
                    if counter == attempts - 1:
                        raise
                    x = str(x)
                    if 'being accessed by other users' not in x:
                        raise
                time.sleep(0.5)
            ConnectionWrapper.committed = False
            ConnectionWrapper.dirty = False
            PgTestSetup._last_db = (self.template, self.dbname)
            PgTestSetup._reset_db = False
        finally:
            con.close()

    def tearDown(self):
        '''Close all outstanding connections and drop the database'''
        while self.connections:
            con = self.connections[-1]
            con.close() # Removes itself from self.connections
        if (ConnectionWrapper.committed and ConnectionWrapper.dirty):
            PgTestSetup._reset_db = True
        ConnectionWrapper.committed = False
        ConnectionWrapper.dirty = False
        if PgTestSetup._reset_db:
            self.dropDb()
            PgTestSetup._reset_db = True
        #uninstallFakeConnect()

    def connect(self):
        """Get an open DB-API Connection object to a temporary database"""
        con = psycopg.connect(
            self._connectionString(self.dbname, self.dbuser)
            )
        return ConnectionWrapper(con)

    def dropDb(self):
        '''Drop the database if it exists.

        Raises an exception if there are open connections
        '''
        attempts = 100
        for i in range(0, attempts):
            try:
                con = psycopg.connect(self._connectionString(self.template))
            except psycopg.OperationalError, x:
                if 'does not exist' in x:
                    return
                raise
            try:
                con.set_isolation_level(0)

                # Kill all backend connections if this helper happens to be
                # available. We could create it if it doesn't exist if not
                # always having this is a problem.
                try:
                    cur = con.cursor()
                    cur.execute('SELECT _killall_backends(%s)', [self.dbname])
                except psycopg.ProgrammingError:
                    pass

                # Drop the database, trying for a number of seconds in case
                # connections are slow in dropping off.
                try:
                    cur = con.cursor()
                    cur.execute('DROP DATABASE %s' % self.dbname)
                except psycopg.ProgrammingError, x:
                    if i == attempts - 1:
                        # Too many failures - raise an exception
                        raise
                    if 'being accessed by other users' in str(x):
                        if i < attempts - 1:
                            time.sleep(0.1)
                            continue
                    if 'does not exist' in str(x):
                        break
                    raise
            finally:
                con.close()

    def force_dirty_database(self):
        """flag the database as being dirty

        This ensures that the database will be recreated for the next test.
        Tearing down the database is done automatically when we detect
        changes. Currently, however, not all changes are detectable (such
        as database changes made from a subprocess.
        """
        PgTestSetup._reset_db = True


class PgTestCase(unittest.TestCase):
    dbname = None
    dbuser = None
    host = None
    port = None
    template = None
    def setUp(self):
        pg_test_setup = PgTestSetup(
                self.template, self.dbname, self.dbuser, self.host, self.port
                )
        pg_test_setup.setUp()
        self.dbname = pg_test_setup.dbname
        self.dbuser = pg_test_setup.dbuser
        assert self.dbname, 'self.dbname is not set.'

    def tearDown(self):
        PgTestSetup(
                self.template, self.dbname, self.dbuser, self.host, self.port
                ).tearDown()

    def connect(self):
        return PgTestSetup(
                self.template, self.dbname, self.dbuser, self.host, self.port
                ).connect()

