# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""XXX: Module docstring goes here."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.services.features.xmlrpc import FeatureFlagApplication
from lp.testing import (
    feature_flags,
    set_feature_flag,
    TestCase,
    )

class TestGetFeatureFlag(TestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCase.setUp(self)
        self.endpoint = FeatureFlagApplication()

    def test_getFeatureFlag_returns_false_by_default(self):
        self.assertFalse(self.endpoint.getFeatureFlag(u'unknown'))

    def test_getFeatureFlag_returns_true_for_set_flag(self):
        flag_name = u'flag'
        with feature_flags():
            set_feature_flag(flag_name, u'1')
            self.assertEqual(u'1', self.endpoint.getFeatureFlag(flag_name))
