import unittest
import os, os.path
import re
import time
from warnings import warn

import psycopg

from zope.app import zapi
from zope.component.exceptions import ComponentLookupError
from zope.component.servicenames import Utilities
from zope.component import getService
from zope.app.rdb.interfaces import IZopeDatabaseAdapter
from sqlos.interfaces import IConnectionName


class ConWrapper:
    """A wrapper around the real connection that ensures all cursors
    are closed.

    This ensures that no tables remain locked causing our tearDown
    method to hang.

    """
    _con = None
    _curs = None

    def __init__(self, con):
        self.__dict__['_con'] = con
        self.__dict__['_curs'] = []

    def cursor(self):
        c = self._con.cursor()
        self._curs.append(c)
        return c

    def close(self):
        for c in self._curs:
            try:
                c.close()
            except psycopg.InterfaceError, x:
                if 'already closed' in str(x):
                    pass
                else:
                    raise
        return self._con.close()

    def __getattr__(self, key):
        return getattr(self.__dict__['_con'], key)

    def __setattr__(self, key, value):
        return setattr(self.__dict__['_con'], key, value)

def PgTestCaseSetUp(template, dbname):
    db_adapter = None
    try:
        name = zapi.getUtility(IConnectionName).name
        db_adapter = zapi.getUtility(IZopeDatabaseAdapter, name)
        if db_adapter.isConnected():
            # we have to disconnect long enough to drop
            # and recreate the DB
            db_adapter.disconnect()
    except ComponentLookupError, err:
        # configuration not yet loaded, no worries
        pass

    con = psycopg.connect('dbname=%s' % template)
    try:
        try:
            cur = con.cursor()
            cur.execute('ABORT TRANSACTION')
            cur.execute('DROP DATABASE %s' % dbname)
        except psycopg.ProgrammingError, x:
            if 'does not exist' not in str(x):
                raise
        for i in range(0,100):
            try:
                cur.execute(
                    "CREATE DATABASE %s TEMPLATE=%s ENCODING='UNICODE'" % (
                        dbname, template))
                break
            except psycopg.ProgrammingError, x:
                x = str(x)
                if 'being accessed by other users' not in x:
                    raise
            time.sleep(0.1)
    finally:
        try:
            if db_adapter and not db_adapter.isConnected():
                # the dirty deed is done, time to reconnect
                db_adapter.connect()

            con.close()
        except psycopg.Error:
            pass

def PgTestCaseTearDown(template, dbname):
    for i in range(0,100):
        try:
            con = psycopg.connect('dbname=%s' % template)
        except psycopg.OperationalError, x:
            if 'does not exist' in x:
                return
            raise
        cur = con.cursor()
        cur.execute('ABORT TRANSACTION')
        try:
            cur.execute('DROP DATABASE %s' % dbname)
        except psycopg.ProgrammingError, x:
            x = str(x)
            if 'being accessed by other users' in x:
                time.sleep(0.1)
                continue
            if 'does not exist' not in str(x):
                raise

class PgTestCase(unittest.TestCase):
    """This test harness will create and destroy a database
    in the setUp and tearDown methods."""

    _cons = None
    dbname = 'unittest_tmp'
    template = 'template1'

    def connect(self):
        """Get an open DB-API Connection object to a temporary database"""
        con = psycopg.connect('dbname=%s' % self.dbname)
        self._cons.append(con)
        return con

    def setUp(self):
        self._cons = []
        PgTestCaseSetUp(self.template, self.dbname)

    def tearDown(self):
        # Close any unclosed connections if our tests are being lazy
        for con in self._cons:
            try:
                con.commit()
                con.close()
            except psycopg.InterfaceError:
                pass # Already closed
        PgTestCaseTearDown(self.template, self.dbname)

