import unittest
from pgsql import PgTestCase, LaunchpadSchemaTestCase
import psycopg

class TestPgTestCase(PgTestCase):

    def test(self):
        con = self.connect()
        cur = con.cursor()
        cur.execute('CREATE TABLE foo (x int)')
        cur.execute('INSERT INTO foo VALUES (1)')
        cur.execute('SELECT x FROM foo')
        res = list(cur.fetchall())
        self.failUnless(len(res) == 1)
        self.failUnless(res[0][0] == 1)
        con.commit()

        self.tearDown()
        try:
            cur = con.cursor()
            self.fail('Cursor not closed in tearDown')
        except psycopg.InterfaceError:
            pass
        con = self.connect()
        cur = con.cursor()
        try:
            cur.execute('SELECT x FROM foo')
            self.fail('Table not deleted in tearDown')
        except psycopg.ProgrammingError:
            pass

class TestLaunchpadSchemaTestCase(LaunchpadSchemaTestCase):
    def test(self):
        con = self.connect()
        cur = con.cursor()
        cur.execute("""
            SELECT count(*) FROM person 
            WHERE presentationname='Mark Shuttleworth'
            """)
        r = cur.fetchone()
        self.failUnlessEqual(r[0], 1)
        cur.close()
        con.close()

def test_suite():
    suite = unittest.TestSuite()
    # XXX: These tests require a launchpad_unittest database to be set up.
    #      They should be rewritten as functional tests.
    ##suite.addTest(unittest.makeSuite(TestPgTestCase))
    ##suite.addTest(unittest.makeSuite(TestLaunchpadSchemaTestCase))
    return suite

if __name__ == '__main__':
    unittest.main()

