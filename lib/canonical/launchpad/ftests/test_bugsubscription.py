import unittest
from zope.testing.doctest import DocFileSuite, DocTestSuite
from canonical.functional import FunctionalTestSetup

def setUp(junk):
    FunctionalTestSetup().setUp()

def tearDown(junk):
    FunctionalTestSetup().tearDown()

def test_suite():
    suite = unittest.TestSuite([
        DocFileSuite('../doc/bugsubscription.txt', setUp=setUp, tearDown=tearDown)])
    return suite

if __name__ == '__main__':
    unittest.main(test_suite())
