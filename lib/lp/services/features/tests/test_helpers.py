# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the feature flags test helpers."""

from __future__ import with_statement


__metaclass__ = type
__all__ = []


from lp.testing import TestCase
from lp.services.features import getFeatureFlag
from lp.services.features.testing import FeatureFixture


class TestFeaturesContextManager(TestCase):
    """Tests for the feature flags context manager test helper."""

    def test_setting_one_flag_with_manager(self):
        flag = self.getUniqueString()
        value_outside_manager = getFeatureFlag(flag)
        value_in_manager = None

        with FeatureFixture({flag: 'on'}):
            value_in_manager = getFeatureFlag(flag)

        self.assertEqual(value_in_manager, 'on')
        self.assertEqual(value_outside_manager, getFeatureFlag(flag))
        self.assertNotEqual(value_outside_manager, value_in_manager)


class TestFeaturesFixture(TestCase):
    """Tests for the feature flags test fixture."""

    def test_fixture_sets_one_flag_and_cleans_up_again(self):
        flag = self.getUniqueString()
        value_before_fixture_setup = getFeatureFlag(flag)
        value_after_fixture_setup = None

        fixture = FeatureFixture({flag: 'on'})
        fixture.setUp()
        value_after_fixture_setup = getFeatureFlag(flag)
        fixture.cleanUp()

        self.assertEqual(value_after_fixture_setup, 'on')
        self.assertEqual(value_before_fixture_setup, getFeatureFlag(flag))
        self.assertNotEqual(
            value_before_fixture_setup, value_after_fixture_setup)

    def test_fixture_keeps_previously_set_feature_values(self):
        self.useFixture(FeatureFixture({'one': 1}))
        self.useFixture(FeatureFixture({'two': 2}))

        self.assertEqual(getFeatureFlag('one'), 1)
        self.assertEqual(getFeatureFlag('two'), 2)

    def test_fixture_overrides_previously_set_flags(self):
        self.useFixture(FeatureFixture({'one': 1}))
        self.useFixture(FeatureFixture({'one': 5}))

        self.assertEqual(getFeatureFlag('one'), 5)
