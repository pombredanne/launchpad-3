# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for setting bug task status."""

__metaclass__ = type

from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.testing import TestCaseWithFactory


class TestBugTaskStatusSetting(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_bug_supervisor_statuses(self):
        self.assertEqual(True, False)


