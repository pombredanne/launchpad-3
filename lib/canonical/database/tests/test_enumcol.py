# Copyright 2005 Canonical Ltd.  All rights reserved.

import unittest
from zope.testing import doctest
import canonical.database.enumcol

def test_suite():
    return doctest.DocTestSuite(canonical.database.enumcol)

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(test_suite())
