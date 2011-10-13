# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Run launchpad.database functional doctests"""

__metaclass__ = type
import unittest

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite
from canonical.testing.layers import LaunchpadFunctionalLayer


def test_suite():
    suite = unittest.TestLoader().loadTestsFromName(__name__)
    suite.addTests([
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
        ])
    return suite
