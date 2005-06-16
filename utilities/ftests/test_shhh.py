# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest
from doctest import DocTestSuite
import sys, os
sys.path.insert(0, os.pardir)

def test_suite():
    return DocTestSuite('shhh')


if __name__ == '__main__':
    default = test_suite()
    unittest.main(defaultTest='default')
