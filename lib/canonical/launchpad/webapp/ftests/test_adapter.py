# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Run launchpad.database functional doctests"""

__metaclass__ = type
import unittest
from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite
from canonical.testing import LaunchpadFunctionalLayer, PageTestLayer

def test_suite():
    return unittest.TestSuite((
        LayeredDocFileSuite(
            'test_adapter.txt',
            layer=LaunchpadFunctionalLayer),
        LayeredDocFileSuite(
            'test_adapter_timeout.txt',
            layer=PageTestLayer),
        ))
