# Copyright 2004 Canonical Ltd.  All rights reserved.
'''
Test harness for tests needing a PostgreSQL backend.
'''

__metaclass__ = type

import unittest
import os, os.path
import re
import time
from warnings import warn

import psycopg
from zope.app.rdb.interfaces import DatabaseException

class ConnectionWrapper(object):
    real_connection = None
    committed = False

    def __init__(self, real_connection):
        self.__dict__['real_connection'] = real_connection
        PgTestSetup.connections.append(self)

    def close(self):
        if self in PgTestSetup.connections:
            PgTestSetup.connections.remove(self)
            self.__dict__['real_connection'].close()

    def rollback(self):
        # In our test suites, rollback ends up being called twice in some
        # circumstances. Silently ignoring this is probably not correct,
        # but the alternative is wasting further time chasing this 
        # and probably refactoring sqlos and/or zope3
        # -- StuartBishop 2005-01-11
        try:
            self.__dict__['real_connection'].rollback()
        except psycopg.InterfaceError:
            pass

    def commit(self):
        # flag that a connection has had commit called. This allows
        # optimizations by subclasses, since if no commit has been made,
        # dropping and recreating the database might be unnecessary
        try:
            return self.__dict__['real_connection'].commit()
        finally:
            ConnectionWrapper.committed = True

    def __getattr__(self, key):
        return getattr(self.__dict__['real_connection'], key)

    def __setattr__(self, key, val):
        return setattr(self.__dict__['real_connection'], key, val)

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
    dbname = 'unittest_tmp'
    dbuser = None

    def __init__(self, template=None, dbname=None, dbuser=None):
        if template is not None:
            self.template = template
        if dbname is not None:
            self.dbname = dbname
        if dbuser is not None:
            self.dbuser = dbuser

    def setUp(self, reset_db=True):
        '''Create a fresh database (dropping the old if necessary)

        Skips db creation if reset_db is False
        '''
        #installFakeConnect()
        if not reset_db:
            return
        self.dropDb()
        con = psycopg.connect('dbname=%s' % self.template)
        try:
            try:
                cur = con.cursor()
                cur.execute('ABORT TRANSACTION')
                cur.execute('DROP DATABASE %s' % self.dbname)
            except psycopg.ProgrammingError, x:
                if 'does not exist' not in str(x):
                    raise
            for i in range(0,100):
                try:
                    cur.execute(
                        "CREATE DATABASE %s TEMPLATE=%s ENCODING='UNICODE'" % (
                            self.dbname, self.template))
                    break
                except psycopg.ProgrammingError, x:
                    x = str(x)
                    if 'being accessed by other users' not in x:
                        raise
                time.sleep(0.1)
            ConnectionWrapper.committed = False
        finally:
            con.close()

    def tearDown(self, reset_db=True):
        '''Close all outstanding connections and drop the database'''
        while self.connections:
            con = self.connections[-1]
            con.close() # Removes itself from self.connections
        if reset_db:
            self.dropDb()
        #uninstallFakeConnect()

    def connect(self):
        """Get an open DB-API Connection object to a temporary database"""
        con = ConnectionWrapper(psycopg.connect('dbname=%s' % self.dbname))
        return con

    def dropDb(self):
        '''Drop the database if it exists.
        
        Raises an exception if there are open connections
        
        '''
        attempts = 100
        for i in range(0, attempts):
            try:
                con = psycopg.connect('dbname=%s' % self.template)
            except psycopg.OperationalError, x:
                if 'does not exist' in x:
                    return
                raise
            try:
                cur = con.cursor()
                cur.execute('ABORT TRANSACTION')
                try:
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

class PgTestCase(unittest.TestCase):
    dbname = None
    template = None
    def setUp(self):
        PgTestSetup(self.template, self.dbname).setUp()

    def tearDown(self):
        PgTestSetup(self.template, self.dbname).tearDown()

    def connect(self):
        return PgTestSetup().connect()

