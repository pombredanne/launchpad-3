# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for feature flag change log."""


__metaclass__ = type

from datetime import datetime

import pytz

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.services.features.model import FeatureFlagChange
from lp.services.features.changelog import ChangeLog
from lp.testing import TestCase


diff = (
    u"-bugs.new_feature team:testers 10 on\n"
    u"+bugs.new_feature team:testers 10 off")


class TestFeatureFlagChange(TestCase):
    """Test the FeatureFlagChange data."""

    layer = DatabaseFunctionalLayer

    def test_FeatureFlagChange_creation(self):
        # A FeatureFlagChange has a diff and a date of change.
        before = datetime.now(pytz.timezone('UTC'))
        feature_flag_change = FeatureFlagChange(diff)
        after = datetime.now(pytz.timezone('UTC'))
        self.assertEqual(
            diff, feature_flag_change.diff)
        self.assertBetween(
            before, feature_flag_change.date_changed, after)


class TestChangeLog(TestCase):
    """Test the feature flag ChangeLog utility."""

    layer = DatabaseFunctionalLayer

    def test_ChangeLog_append(self):
        # The append() method creates a FeatureFlagChange.
        feature_flag_change = ChangeLog.append(diff)
        self.assertEqual(
            diff, feature_flag_change.diff)

    def test_ChangeLog_get(self):
        # The get() method returns an iterator of FeatureFlagChanges from
        # newest to oldest.
        feature_flag_change_1 = ChangeLog.append(diff)
        feature_flag_change_2 = ChangeLog.append(diff)
        results = ChangeLog.get()
        self.assertEqual(
            [feature_flag_change_2, feature_flag_change_1], list(results))
