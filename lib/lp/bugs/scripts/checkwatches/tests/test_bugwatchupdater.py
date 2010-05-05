# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the checkwatches.bugwatchupdater module."""

__metaclass__ = type

import transaction
import unittest

from canonical.testing import LaunchpadZopelessLayer

from lp.bugs.interfaces.bugtask import BugTaskImportance, BugTaskStatus
from lp.bugs.scripts.checkwatches.bugwatchupdater import BugWatchUpdater
from lp.bugs.scripts.checkwatches.core import CheckwatchesMaster
from lp.bugs.tests.externalbugtracker import TestExternalBugTracker
from lp.testing import TestCaseWithFactory


class BugWatchUpdaterTestCase(TestCaseWithFactory):
    """Tests the functionality of the BugWatchUpdater class."""

    layer = LaunchpadZopelessLayer

    def test_updateBugWatch(self):
        # Calling BugWatchUpdater.updateBugWatch() will update the
        # updater's current BugWatch.
        checkwatches_master = CheckwatchesMaster(transaction)
        bug_watch = self.factory.makeBugWatch()
        bug_watch_updater = BugWatchUpdater(
            checkwatches_master, bug_watch,
            TestExternalBugTracker('http://example.com'))

        bug_watch_updater.updateBugWatch(
            'FIXED', BugTaskStatus.FIXRELEASED, 'LOW',
            BugTaskImportance.LOW, can_import_comments=False,
            can_push_comments=False, can_back_link=False)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
