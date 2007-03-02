# Copyright 2007 Canonical Ltd.  All rights reserved.


import unittest, doctest

def test_suite():
    suite = unittest.TestSuite()
    #suite.layer = unit test
    suite.addTest(doctest.DocTestSuite(
        'canonical.launchpad.browser.openidserver'
        ))
    return suite

