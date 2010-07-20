# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BugTracker views."""

__metaclass__ = type

import unittest

from datetime import datetime, timedelta
from pytz import utc

from zope.component import getUtility
from zope.security.interfaces import Unauthorized

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing.layers import DatabaseFunctionalLayer

from lp.bugs.browser.bugtracker import (
    BugTrackerEditView)
from lp.registry.interfaces.person import IPersonSet
from lp.testing import login, TestCaseWithFactory
from lp.testing.sampledata import ADMIN_EMAIL, NO_PRIVILEGE_EMAIL
from lp.testing.views import create_initialized_view


class BugTrackerEditViewTestCase(TestCaseWithFactory):
    """A TestCase for the `BugTrackerEditView`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(BugTrackerEditViewTestCase, self).setUp()
        self.bug_tracker = self.factory.makeBugTracker()
        for i in range(5):
            self.factory.makeBugWatch(bugtracker=self.bug_tracker)

        self.now = datetime.now(utc)

    def _assertBugWatchesAreCheckedInTheFuture(self):
        """Check the dates of all self.bug_tracker.watches.

        Raise an error if:
         * The next_check dates aren't in the future.
         * The next_check dates aren't <= 1 day in the future.
         * The lastcheck dates are not None
         * The last_error_types are not None.
        """
        for watch in self.bug_tracker.watches:
            self.assertTrue(
                watch.next_check is not None,
                "BugWatch next_check time should not be None.")
            self.assertTrue(
                watch.next_check >= self.now,
                "BugWatch next_check time should be in the future.")
            self.assertTrue(
                watch.next_check <= self.now + timedelta(days=1),
                "BugWatch next_check time should be one day or less in "
                "the future.")
            self.assertTrue(
                watch.lastchecked is None,
                "BugWatch lastchecked should be None.")
            self.assertTrue(
                watch.last_error_type is None,
                "BugWatch last_error_type should be None.")

    def test_unprivileged_user_cant_reset_watches(self):
        # It isn't possible for a user who isn't an admin or a member of
        # the Launchpad Developers team to reset the watches for a bug
        # tracker.
        login(NO_PRIVILEGE_EMAIL)
        view = create_initialized_view(self.bug_tracker, '+edit')
        self.assertRaises(
            Unauthorized, view.resetBugTrackerWatches)

    def test_admin_can_reset_watches(self):
        # Launchpad admins can reset the watches on a bugtracker.
        login(ADMIN_EMAIL)
        view = create_initialized_view(self.bug_tracker, '+edit')
        view.resetBugTrackerWatches()
        self._assertBugWatchesAreCheckedInTheFuture()

    def test_lp_dev_can_reset_watches(self):
        # Launchpad developers can reset the watches on a bugtracker.
        login(ADMIN_EMAIL)
        admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        launchpad_developers = getUtility(
            ILaunchpadCelebrities).launchpad_developers

        lp_dev = self.factory.makePerson()
        launchpad_developers.addMember(lp_dev, admin)

        login(lp_dev.preferredemail.email)
        view = create_initialized_view(self.bug_tracker, '+edit')
        view.resetBugTrackerWatches()
        self._assertBugWatchesAreCheckedInTheFuture()


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
