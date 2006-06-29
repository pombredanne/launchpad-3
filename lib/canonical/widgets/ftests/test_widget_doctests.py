# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest, doctest
from canonical.testing.layers import LaunchpadFunctional

def test_suite():
    suite = doctest.DocTestSuite('canonical.widgets.password')
    suite.layer = LaunchpadFunctional
    return suite

if __name__ == '__main__':
    default_test = test_suite()
    unittest.main('default_test')
