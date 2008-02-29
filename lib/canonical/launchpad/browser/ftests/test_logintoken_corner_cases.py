# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test harness for running the logintoken-corner-cases.txt tests."""

__metaclass__ = type

import unittest

from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.testing import LaunchpadFunctionalLayer


def test_suite():
    suite = unittest.TestSuite()

    test = LayeredDocFileSuite('logintoken-corner-cases.txt',
        setUp=setUp, tearDown=tearDown,
        layer=LaunchpadFunctionalLayer)
    suite.addTest(test)
    return suite
