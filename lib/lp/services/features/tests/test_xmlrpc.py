# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""XXX: Module docstring goes here."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.services.features.xmlrpc import FeatureFlagApplication
from lp.testing import TestCase

class TestGetFeatureFlag(TestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCase.setUp(self)
        self.endpoint = FeatureFlagApplication()

    # XXX: Sample test.  Replace with your own test methods.
    def test_getFeatureFlag_returns_false_by_default(self):
        self.assertFalse(self.endpoint.getFeatureFlag('unknown'))
