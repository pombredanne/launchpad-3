import unittest, os, os.path, re, time
import psycopg
from warnings import warn
import time

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


class PgTestCase(unittest.TestCase):
    """This test harness will create and destroy a database 
       in the setUp and tearDown methods

    """
    # This database must already exist
    _cons = None
    dbname = 'unittest_tmp'
    template = 'template1'

    def connect(self):
        """Get an open DB-API Connection object to a temporary database"""
        con = psycopg.connect('dbname=%s' % self.dbname)
        #con = ConWrapper(con)
        self._cons.append(con)
        return con

    def setUp(self):
        self._cons = []
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
                            self.dbname, self.template
                            )
                        )
                    break
                except psycopg.ProgrammingError, x:
                    x = str(x)
                    if 'being accessed by other users' not in x:
                        raise
                time.sleep(0.1)
        finally:
            try:
                con.close()
            except psycopg.Error:
                pass
 
    def tearDown(self):
        # Close any unclosed connections if our tests are being lazy
        for con in self._cons:
            try:
                con.commit()
                con.close()
            except psycopg.InterfaceError:
                pass # Already closed
        for i in range(0,100):
            try:
                con = psycopg.connect('dbname=%s' % self.template)
            except psycopg.OperationalError, x:
                if 'does not exist' in x:
                    return
                raise
            cur = con.cursor()
            cur.execute('ABORT TRANSACTION')
            try:
                cur.execute('DROP DATABASE %s' % self.dbname)
            except psycopg.ProgrammingError, x:
                x = str(x)
                if 'being accessed by other users' in x:
                    time.sleep(0.1)
                    continue
                if 'does not exist' not in str(x):
                    raise

