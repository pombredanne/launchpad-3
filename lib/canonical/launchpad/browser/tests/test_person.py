# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test harness for person views unit tests."""

__metaclass__ = type

__all__ = []

import unittest

from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.testing.layers import DatabaseFunctionalLayer


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))
    suite.addTest(LayeredDocFileSuite(
        'person-rename-account.txt',
        setUp=setUp, tearDown=tearDown,
        layer=DatabaseFunctionalLayer))
    return suite


if __name__ == '__main__':
    unittest.main()

