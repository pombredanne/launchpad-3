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
            con = psycopg.connect('dbname=%s' % self.template)
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


class LaunchpadSchemaTestCase(PgTestCase):
    dbname = 'launchpad_unittest'
    template = 'launchpad_unittest_template'

"""
    def resetDatabase(self):
        con = self.connect()
        cur = con.cursor()
        full_sql = '''
            select c.relname, relkind from pg_class c, pg_namespace n
            where n.oid = c.relnamespace
            and n.nspname not in ('pg_catalog','pg_toast')
            and pg_table_is_visible(c.oid)
            '''
        type_sql = full_sql + 'and c.relkind = %(kind)s'
        cur.execute(type_sql, {'kind': 'r'})
        def quote_table(t):
            t = psycopg.QuotedString(t)
            t = '"' + str(t)[1:-1] + '"'
            return t
        tables = [quote_table(r[0]) for r in cur.fetchall()]
        for table in tables:
            cur.execute('END TRANSACTION')
            try:
                cur.execute('DROP TABLE %s CASCADE' % table)
            except psycopg.ProgrammingError, x:
                if 'does not exist' in str(x):
                    pass
                else:
                    raise

        # Confirm they are all deleted, or warn
        cur.execute(type_sql, {'kind': 'r'})
        tables = [r[0] for r in cur.fetchall()]
        for table in tables:
            warn('Table %r not dropped' % (table,))
"""


'''
class LaunchpadSchemaTestCase(PgTestCase):
    """A test harness that creates the launchpad database schema and populates
    it with the current sample data

    """
    def _getSQL(self, fname):
        path = os.path.join(
                os.path.dirname(__file__),
                os.pardir, os.pardir, os.pardir, 'database', fname
                )
        raw = open(path, 'r').read()
        stripper = re.compile(r"/\*.*?\*/", re.MULTILINE | re.DOTALL)
        m = stripper.subn('', raw)[0]
        stripper = re.compile(r"--.*$", re.MULTILINE)
        m = stripper.subn('', m)[0]
        splitter = re.compile(r"^(.+?);\s*$", re.MULTILINE | re.DOTALL)
        m = [cmd.strip() for cmd in splitter.findall(m) if cmd.strip()]
        m = [m for m in m if not m.startswith('DROP TABLE')]
        return m

    def setUp(self):
        PgTestCase.setUp(self)
        con = self.connect()
        cur = con.cursor()
        try:
            schema = self._getSQL('sampledata/current.sql')
            for sql in schema:
                cur.execute(sql)
            con.commit()
            schema = self._getSQL('default.sql')
            for sql in schema:
                cur.execute(sql)
            con.commit()
        finally:
            cur.close()
            con.close()
'''
