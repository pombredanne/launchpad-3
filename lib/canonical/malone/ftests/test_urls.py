import unittest
from malonesql import MaloneSQLTestCase
from canonical.tests.functional import BrowserTestCase
from canonical.tests.pgsql import PgTestCase

class MaloneURLTestCase(MaloneSQLTestCase):
    def fetch(self, page):
        response = self.publish(page)
        self.failUnlessEqual(response.getStatus(), 200)
        return response.getBogy().strip()

    def test_bugs(self):
        '/malone/bugs/index'
        r1 = self.fetch('/malone/bugs')
        r2 = self.fetch('/malone/bugs/index')
        self.failUnlessEqual(r1, r2)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(MaloneURLTestCase))
    return suite

if __name__ == '__main__':
    unittest.main()

