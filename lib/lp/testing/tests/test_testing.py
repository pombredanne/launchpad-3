# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the testing module."""

__metaclass__ = type

import os
import tempfile

from canonical.config import config
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.services.features import getFeatureFlag
from lp.testing import (
    feature_flags,
    nested_tempfile,
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


class NestedTempfileTest(TestCase):
    """Tests for `nested_tempfile`."""

    def test_normal(self):
        # The temp directory is removed when the context is exited.
        starting_tempdir = tempfile.gettempdir()
        with nested_tempfile() as tempdir:
            self.assertEqual(tempdir, tempfile.gettempdir())
            self.assertEqual(tempdir, tempfile.tempdir)
            self.assertNotEqual(tempdir, starting_tempdir)
            self.assertTrue(os.path.isdir(tempdir))
        self.assertEqual(starting_tempdir, tempfile.gettempdir())
        self.assertEqual(starting_tempdir, tempfile.tempdir)
        self.assertFalse(os.path.isdir(tempdir))

    def test_exception(self):
        # The temp directory is removed when the context is exited, even if
        # the code running in context raises an exception.
        class ContrivedException(Exception):
            pass
        try:
            with nested_tempfile() as tempdir:
                raise ContrivedException
        except ContrivedException:
            self.assertFalse(os.path.isdir(tempdir))
