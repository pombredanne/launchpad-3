# Copyright 2005 Canonical Ltd.  All rights reserved.

import unittest
from zope.testing import doctest
import canonical.database.datetimecol

def test_suite():
    return doctest.DocTestSuite(canonical.database.datetimecol)

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(test_suite())
