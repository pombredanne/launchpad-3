import unittest
from canonical.ftests.pgsql import PgTestCase
import psycopg

class TestPgTestCase(PgTestCase):

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


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPgTestCase))
    return None

if __name__ == '__main__':
    unittest.main()

