# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the doctests in the product module."""

# XXX sinzui 2009-04-03 bug=354881: This test harness should be removed
# and the inline tests moved to docs/

__metaclass__ = type

from doctest import DocTestSuite
import unittest

from canonical.launchpad.testing.systemdocs import (
    setUp,
    tearDown,
    )
from canonical.testing.layers import LaunchpadFunctionalLayer
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
