# Copyright 2004 Canonical Ltd.  All rights reserved.

from canonical.database import sqlbase
import unittest, doctest

def test_suite():
    dt_suite = doctest.DocTestSuite(sqlbase)
    return unittest.TestSuite((dt_suite,))

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(test_suite())
