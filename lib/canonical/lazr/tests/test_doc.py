# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test harness for LAZR doctests."""

__metaclass__ = type
__all__ = []

import unittest
import doctest

def test_suite():
    options = (doctest.ELLIPSIS|
               doctest.NORMALIZE_WHITESPACE|
               doctest.REPORT_NDIFF)
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocFileSuite(
        '../doc/debug.txt', optionflags=options))
    suite.addTest(doctest.DocFileSuite(
        '../doc/interface.txt', optionflags=options))
    return suite

