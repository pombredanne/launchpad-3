import unittest
import canonical.tests.pgsql as pgsql
import psycopg

class TestPgTestCase(pgsql.PgTestCase):

    def testRollback(self):
        # This test creates a table. We run the same test twice,
        # which will fail if database changes are not rolled back
        con = self.connect()
        cur = con.cursor()
        cur.execute('CREATE TABLE foo (x int)')
        cur.execute('INSERT INTO foo VALUES (1)')
        cur.execute('SELECT x FROM foo')
        res = list(cur.fetchall())
        self.failUnless(len(res) == 1)
        self.failUnless(res[0][0] == 1)
        con.commit()

    testRollback2 = testRollback


class TestLaunchpadSchemaTestCase(pgsql.LaunchpadSchemaTestCase):
    def test(self):
        con = self.connect()
        cur = con.cursor()
        cur.execute("""
            SELECT count(*) FROM Person 
            WHERE displayname='Mark Shuttleworth'
            """)
        r = cur.fetchone()
        self.failUnlessEqual(r[0], 1, 'Sample data not loaded')
        cur.close()
        con.close()

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPgTestCase))
    suite.addTest(unittest.makeSuite(TestLaunchpadSchemaTestCase))
    return None

if __name__ == '__main__':
    unittest.main()

