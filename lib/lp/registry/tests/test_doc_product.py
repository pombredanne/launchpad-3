# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test the doctests in the product module."""

# XXX sinzui 2009-04-03 bug=354881: This test harness shold be removed
# and the inline tests moved to docs/

__metaclass__ = type

import unittest

from doctest import DocTestSuite

from canonical.launchpad.testing.systemdocs import setUp, tearDown
from canonical.testing import LaunchpadFunctionalLayer
from lp.registry.interfaces import product


def test_suite():
    suite = unittest.TestSuite()
    test = DocTestSuite(product, setUp=setUp, tearDown=tearDown)
    test.layer = LaunchpadFunctionalLayer
    suite.addTest(test)
    return suite


if __name__ == '__main__':
    DEFAULT = test_suite()
    unittest.main('DEFAULT')
