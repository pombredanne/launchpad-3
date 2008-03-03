# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Tests for the validators."""

__metaclass__ = type

import unittest

from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.testing.layers import LaunchpadFunctionalLayer


def test_suite():
    suite = unittest.TestSuite()
    test = LayeredDocFileSuite(
        'validation.txt', setUp=setUp, tearDown=tearDown,
        layer=LaunchpadFunctionalLayer)
    suite.addTest(test)
    return suite


if __name__ == '__main__':
    unittest.main()
