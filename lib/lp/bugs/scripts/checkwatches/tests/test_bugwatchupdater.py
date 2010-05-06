# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the checkwatches.bugwatchupdater module."""

__metaclass__ = type

import transaction
import unittest

from canonical.testing import LaunchpadZopelessLayer

from lp.bugs.interfaces.bugtask import BugTaskImportance, BugTaskStatus
from lp.bugs.interfaces.bugwatch import BugWatchActivityStatus
from lp.bugs.scripts.checkwatches.bugwatchupdater import BugWatchUpdater
from lp.bugs.scripts.checkwatches.core import CheckwatchesMaster
from lp.bugs.tests.externalbugtracker import TestExternalBugTracker
from lp.testing import TestCaseWithFactory


class BrokenCommentSyncingExternalBugTracker(TestExternalBugTracker):
    """An ExternalBugTracker that can't sync comments."""

    import_comments_error_message = "Can't import comments, sorry."

    def getCommentIds(self, remote_bug_id):
        raise Exception(self.import_comments_error_message)


class BugWatchUpdaterTestCase(TestCaseWithFactory):
    """Tests the functionality of the BugWatchUpdater class."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(BugWatchUpdaterTestCase, self).setUp()
        self.checkwatches_master = CheckwatchesMaster(transaction)
        self.bug_task = self.factory.makeBugTask()
        self.bug_watch = self.factory.makeBugWatch(bug_task=self.bug_task)

    def test_updateBugWatch(self):
        # Calling BugWatchUpdater.updateBugWatch() will update the
        # updater's current BugWatch.
        bug_watch_updater = BugWatchUpdater(
            self.checkwatches_master, self.bug_watch,
            TestExternalBugTracker('http://example.com'))

        bug_watch_updater.updateBugWatch(
            'FIXED', BugTaskStatus.FIXRELEASED, 'LOW',
            BugTaskImportance.LOW, can_import_comments=False,
            can_push_comments=False, can_back_link=False)

        self.assertEqual('FIXED', self.bug_watch.remotestatus)
        self.assertEqual(BugTaskStatus.FIXRELEASED, self.bug_task.status)
        self.assertEqual('LOW', self.bug_watch.remote_importance)
        self.assertEqual(BugTaskImportance.LOW, self.bug_task.importance)
        self.assertEqual(None, self.bug_watch.last_error_type)

        latest_activity = self.bug_watch.activity[0]
        self.assertEqual(
            BugWatchActivityStatus.SYNC_SUCCEEDED, latest_activity.result)

    def test_importBugComments_error_handling(self):
        # If an error occurs when importing bug comments, it will be
        # recorded as BugWatchActivityStatus.COMMENT_IMPORT_FAILED.
        external_bugtracker = BrokenCommentSyncingExternalBugTracker(
            'http://example.com')
        bug_watch_updater = BugWatchUpdater(
            self.checkwatches_master, self.bug_watch, external_bugtracker)

        bug_watch_updater.updateBugWatch(
            'FIXED', BugTaskStatus.FIXRELEASED, 'LOW',
            BugTaskImportance.LOW, can_import_comments=True,
            can_push_comments=False, can_back_link=False)

        latest_activity = self.bug_watch.activity[0]
        self.assertEqual(
            BugWatchActivityStatus.COMMENT_IMPORT_FAILED,
            self.bug_watch.last_error_type)
        self.assertEqual(
            BugWatchActivityStatus.COMMENT_IMPORT_FAILED,
            latest_activity.result)
        self.assertEqual(
            external_bugtracker.import_comments_error_message,
            latest_activity.message)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
