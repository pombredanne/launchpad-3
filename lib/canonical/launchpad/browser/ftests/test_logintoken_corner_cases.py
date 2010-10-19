# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test harness for running the logintoken-corner-cases.txt tests."""

__metaclass__ = type

import unittest

from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite,
    setUp,
    tearDown,
    )
from canonical.testing.layers import LaunchpadFunctionalLayer


def test_suite():
    suite = unittest.TestSuite()

    test = LayeredDocFileSuite('logintoken-corner-cases.txt',
        setUp=setUp, tearDown=tearDown,
        layer=LaunchpadFunctionalLayer)
    suite.addTest(test)
    return suite
