"""Test the examples included in the system documentation in
lib/canonical/launchpad/doc."""

import unittest
from pprint import pprint
from zope.testing.doctest import DocFileSuite, DocTestSuite
from canonical.functional import FunctionalTestSetup

def setUp(junk):
    FunctionalTestSetup().setUp()

def tearDown(junk):
    FunctionalTestSetup().tearDown()

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestSuite([DocFileSuite(
            '../doc/bugsubscription.txt', setUp=setUp, tearDown=tearDown
            )]))
    suite.addTest(unittest.TestSuite([DocFileSuite(
        '../doc/vocabularies.txt', setUp=setUp, tearDown=tearDown
        )]))
    suite.addTest(unittest.TestSuite([DocFileSuite(
        '../doc/bugactivity.txt', setUp=setUp, tearDown=tearDown
        )]))
    suite.addTest(unittest.TestSuite([DocFileSuite(
        '../doc/person.txt', setUp=setUp, tearDown=tearDown
        )]))
    return suite

if __name__ == '__main__':
    unittest.main(test_suite())
