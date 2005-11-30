# Copyright 2004-2005 Canonical Ltd.  All rights reserved.


import unittest
from zope.testing.doctest import DocFileSuite, DocTestSuite

def test_suite():
    suite = unittest.TestSuite([DocFileSuite('test_imports.txt')])
    return suite

