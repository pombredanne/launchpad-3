# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest
from zope.testing.doctestunit import DocTestSuite

def test_suite():
    return DocTestSuite('canonical.rosetta.tar')

if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())


