# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the testing module."""

__metaclass__ = type

import os

from canonical.config import config
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.services.features import getFeatureFlag
from lp.testing import (
    feature_flags,
    set_feature_flag,
    TestCase,
    YUIUnitTestCase,
    )


class TestFeatureFlags(TestCase):

    layer = DatabaseFunctionalLayer

    def test_set_feature_flags_raises_if_not_available(self):
        """set_feature_flags prevents mistakes mistakes by raising."""
        self.assertRaises(AssertionError, set_feature_flag, u'name', u'value')

    def test_flags_set_within_feature_flags_context(self):
        """In the feature_flags context, set/get works."""
        self.useContext(feature_flags())
        set_feature_flag(u'name', u'value')
        self.assertEqual('value', getFeatureFlag('name'))

    def test_flags_unset_outside_feature_flags_context(self):
        """get fails when used outside the feature_flags context."""
        with feature_flags():
            set_feature_flag(u'name', u'value')
        self.assertIs(None, getFeatureFlag('name'))


class TestYUIUnitTestCase(TestCase):

    def test_id(self):
        test = YUIUnitTestCase()
        test.initialize("foo/bar/baz.html")
        self.assertEqual(test.test_path, test.id())

    def test_id_is_normalized_and_relative_to_root(self):
        test = YUIUnitTestCase()
        test_path = os.path.join(config.root, "../bar/baz/../bob.html")
        test.initialize(test_path)
        self.assertEqual("../bar/bob.html", test.id())
