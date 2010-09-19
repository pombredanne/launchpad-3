# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BugTracker views."""

__metaclass__ = type


from canonical.testing.layers import DatabaseFunctionalLayer
from lp.bugs.model.bugtracker import BugTrackerSet
from lp.testing import TestCaseWithFactory
from lp.testing.views import create_initialized_view
from lp.testing.matchers import IsConfiguredBatchNavigator



class TestBugTrackerSetView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_trackers_are_batch_navigators(self):
        trackers = BugTrackerSet()
        view = create_initialized_view(trackers, name='+index')
        matcher = IsConfiguredBatchNavigator('tracker', 'trackers')
        self.assertThat(view.active_trackers, matcher)
        self.assertThat(view.inactive_trackers, matcher)
