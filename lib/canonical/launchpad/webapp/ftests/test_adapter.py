# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Run launchpad.database functional doctests"""

__metaclass__ = type
import unittest

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite
from canonical.launchpad.webapp import adapter
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.testing import TestCase


class TestTimeout(TestCase):

    def test_set_permit_timeout_from_features(self):
        adapter.set_permit_timeout_from_features(True)
        self.assertTrue(adapter._local._permit_feature_timeout)
        adapter.set_permit_timeout_from_features(False)
        self.assertFalse(adapter._local._permit_feature_timeout)

    def test_set_request_started_disables_flag_timeout(self):
        adapter.set_request_started()
        self.addCleanup(adapter.clear_request_started)
        self.assertFalse(adapter._local._permit_feature_timeout)


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
