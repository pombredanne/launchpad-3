# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest, doctest

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite('canonical.widgets.password'))
    return suite

if __name__ == '__main__':
    default_test = test_suite()
    unittest.main('default_test')
