# Copyright 2004 Canonical Ltd.  All rights reserved.

from canonical.database import sqlbase
import unittest, doctest

from zope.testing.doctest import ELLIPSIS, NORMALIZE_WHITESPACE, REPORT_NDIFF


def test_suite():
    optionflags = ELLIPSIS|NORMALIZE_WHITESPACE|REPORT_NDIFF
    dt_suite = doctest.DocTestSuite(sqlbase, optionflags=optionflags)
    return unittest.TestSuite((dt_suite,))

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(test_suite())
