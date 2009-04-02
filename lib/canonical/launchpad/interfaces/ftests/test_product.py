# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test the doctests in the product module."""

__metaclass__ = type

import unittest

from doctest import DocTestSuite

from canonical.launchpad.testing.systemdocs import setUp, tearDown
from canonical.testing import LaunchpadFunctionalLayer
from canonical.launchpad.interfaces import product


def test_suite():
    suite = unittest.TestSuite()
    test = DocTestSuite(product, setUp=setUp, tearDown=tearDown)
    test.layer = LaunchpadFunctionalLayer
    suite.addTest(test)
    return suite


if __name__ == '__main__':
    DEFAULT = test_suite()
    unittest.main('DEFAULT')
