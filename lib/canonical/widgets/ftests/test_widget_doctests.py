# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest, doctest
from canonical.functional import FunctionalTestSetup

def setUp(test):
    FunctionalTestSetup().setUp()

def tearDown(test):
    FunctionalTestSetup().tearDown()

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(
        'canonical.widgets.password', setUp=setUp, tearDown=tearDown
        ))
    return suite

if __name__ == '__main__':
    default_test = test_suite()
    unittest.main('default_test')
