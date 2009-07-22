# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

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
