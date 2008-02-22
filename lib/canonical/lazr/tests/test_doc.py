# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test harness for LAZR doctests."""

__metaclass__ = type
__all__ = []

import doctest
from os import path
import unittest


here = path.dirname(__file__)

docfiles = [
    '../doc/debug.txt',
    '../doc/decorates.txt',
    '../doc/config.txt',
    ]


def test_suite():
    """See `zope.testing.testrunner`."""
    options = (doctest.ELLIPSIS|
               doctest.NORMALIZE_WHITESPACE|
               doctest.REPORT_NDIFF)
    suite = unittest.TestSuite()
    for docfile in docfiles:
        globs = {'__file__' : path.normpath(path.join(here, docfile))}
        test = doctest.DocFileSuite(docfile, optionflags=options, globs=globs)
        suite.addTest(test)
    return suite

