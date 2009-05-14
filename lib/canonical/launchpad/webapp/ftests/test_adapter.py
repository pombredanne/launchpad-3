# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Run launchpad.database functional doctests"""

__metaclass__ = type
import unittest
from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite
from canonical.testing import LaunchpadFunctionalLayer

def test_suite():
    return unittest.TestSuite([
        LayeredDocFileSuite(
            'test_adapter.txt',
            layer=LaunchpadFunctionalLayer),
# XXX Julian 2009-05-13, bug=376171
# Temporarily disabled because of intermittent failures.
#       LayeredDocFileSuite(
#            'test_adapter_timeout.txt',
#            layer=PageTestLayer),
        LayeredDocFileSuite(
            'test_adapter_permissions.txt',
            layer=LaunchpadFunctionalLayer),
        LayeredDocFileSuite(
            'test_adapter_dbpolicy.txt',
            layer=LaunchpadFunctionalLayer),
        ])
