# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the internal codehosting API."""

__metaclass__ = type

import datetime
import pytz
import transaction
import unittest

from zope.component import getUtility

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import cursor
from canonical.launchpad.interfaces import (
    BranchType, IBranchSet, IScriptActivitySet)
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.xmlrpc.codehosting import BranchDetailsStorageAPI
from canonical.testing import DatabaseFunctionalLayer


UTC = pytz.timezone('UTC')


class BranchDetailsStorageTest(TestCaseWithFactory):
    """Tests for the implementation of `IBranchDetailsStorage`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.storage = BranchDetailsStorageAPI(None, None)

    def assertMirrorFailed(self, branch, failure_message, num_failures=1):
        """Assert that `branch` failed to mirror.

        :param branch: The branch that failed to mirror.
        :param failure_message: The last message that the branch failed with.
        :param num_failures: The number of times this branch has failed to
            mirror. Defaults to one.
        """
        self.assertSqlAttributeEqualsDate(
            branch, 'last_mirror_attempt', UTC_NOW)
        self.assertIs(None, branch.last_mirrored)
        self.assertEqual(num_failures, branch.mirror_failures)
        self.assertEqual(failure_message, branch.mirror_status_message)

    def assertMirrorSucceeded(self, branch, revision_id):
        """Assert that `branch` mirrored to `revision_id`."""
        self.assertSqlAttributeEqualsDate(
            branch, 'last_mirror_attempt', UTC_NOW)
        self.assertSqlAttributeEqualsDate(
            branch, 'last_mirrored', UTC_NOW)
        self.assertEqual(0, branch.mirror_failures)
        self.assertEqual(revision_id, branch.last_mirrored_id)

    def assertUnmirrored(self, branch):
        """Assert that `branch` has not yet been mirrored.

        Asserts that last_mirror_attempt, last_mirrored and
        mirror_status_message are all None, and that mirror_failures is 0.
        """
        self.assertIs(None, branch.last_mirror_attempt)
        self.assertIs(None, branch.last_mirrored)
        self.assertEqual(0, branch.mirror_failures)
        self.assertIs(None, branch.mirror_status_message)

    def test_startMirroring(self):
        # startMirroring updates last_mirror_attempt to 'now', leaves
        # last_mirrored alone and returns True when passed the id of an
        # existing branch.
        branch = self.factory.makeBranch()
        self.assertUnmirrored(branch)

        success = self.storage.startMirroring(branch.id)
        self.assertEqual(success, True)

        self.assertSqlAttributeEqualsDate(
            branch, 'last_mirror_attempt', UTC_NOW)
        self.assertIs(None, branch.last_mirrored)

    def test_startMirroring_invalid_branch(self):
        # startMirroring returns False when given a branch id which does not
        # exist.
        invalid_id = -1
        branch = getUtility(IBranchSet).get(invalid_id)
        self.assertIs(None, branch)

        success = self.storage.startMirroring(invalid_id)
        self.assertEqual(success, False)

    def test_mirrorFailed(self):
        branch = self.factory.makeBranch()
        self.assertUnmirrored(branch)

        self.storage.startMirroring(branch.id)
        failure_message = self.factory.getUniqueString()
        success = self.storage.mirrorFailed(branch.id, failure_message)
        self.assertEqual(success, True)
        self.assertMirrorFailed(branch, failure_message)

    def test_mirrorComplete(self):
        # mirrorComplete marks the branch as having been successfully
        # mirrored, with no failures and no status message.
        branch = self.factory.makeBranch()
        self.assertUnmirrored(branch)

        self.storage.startMirroring(branch.id)
        revision_id = self.factory.getUniqueString()
        success = self.storage.mirrorComplete(branch.id, revision_id)
        self.assertEqual(success, True)
        self.assertMirrorSucceeded(branch, revision_id)

    def test_mirrorComplete_resets_failure_count(self):
        # mirrorComplete marks the branch as successfully mirrored and removes
        # all memory of failure.

        # First, mark the branch as failed.
        branch = self.factory.makeBranch()
        self.storage.startMirroring(branch.id)
        failure_message = self.factory.getUniqueString()
        self.storage.mirrorFailed(branch.id, failure_message)
        self.assertMirrorFailed(branch, failure_message)

        # Start and successfully finish a mirror.
        self.storage.startMirroring(branch.id)
        revision_id = self.factory.getUniqueString()
        self.storage.mirrorComplete(branch.id, revision_id)

        # Confirm that it succeeded.
        self.assertMirrorSucceeded(branch, revision_id)

    def test_recordSuccess(self):
        # recordSuccess must insert the given data into ScriptActivity.
        started = datetime.datetime(2007, 07, 05, 19, 32, 1, tzinfo=UTC)
        completed = datetime.datetime(2007, 07, 05, 19, 34, 24, tzinfo=UTC)
        started_tuple = tuple(started.utctimetuple())
        completed_tuple = tuple(completed.utctimetuple())
        success = self.storage.recordSuccess(
            'test-recordsuccess', 'vostok', started_tuple, completed_tuple)
        self.assertEqual(success, True)

        activity = getUtility(IScriptActivitySet).getLastActivity(
            'test-recordsuccess')
        self.assertEqual('vostok', activity.hostname)
        self.assertEqual(started, activity.date_started)
        self.assertEqual(completed, activity.date_completed)


class BranchPullQueueTest(TestCaseWithFactory):
    """Tests for the pull queue methods of `IBranchDetailsStorage`."""

    layer = DatabaseFunctionalLayer

    # XXX:
    # - Was it right to remove the switch to a more restrictive security
    #   proxy?
    # - Making these tests pass has made the xmlrpc-branch-details.txt fail,
    #   probably need to get rid of the sample data.

    def setUp(self):
        super(BranchPullQueueTest, self).setUp()
        self.emptyPullQueues()
        self.storage = BranchDetailsStorageAPI(None, None)

    def assertBranchQueues(self, hosted, mirrored, imported):
        expected_hosted = [
            self.storage._getBranchPullInfo(branch) for branch in hosted]
        expected_mirrored = [
            self.storage._getBranchPullInfo(branch) for branch in mirrored]
        expected_imported = [
            self.storage._getBranchPullInfo(branch) for branch in imported]
        self.assertEqual(
            expected_hosted, self.storage.getBranchPullQueue('HOSTED'))
        self.assertEqual(
            expected_mirrored, self.storage.getBranchPullQueue('MIRRORED'))
        self.assertEqual(
            expected_imported, self.storage.getBranchPullQueue('IMPORTED'))

    def emptyPullQueues(self):
        transaction.begin()
        cursor().execute("UPDATE Branch SET next_mirror_time = NULL")
        transaction.commit()

    def test_pullQueuesEmpty(self):
        """getBranchPullQueue returns an empty list when there are no branches
        to pull.
        """
        self.assertBranchQueues([], [], [])

    def makeBranchAndRequestMirror(self, branch_type):
        """Make a branch of the given type and call requestMirror on it."""
        transaction.begin()
        try:
            branch = self.factory.makeBranch(branch_type)
            branch.requestMirror()
            return branch
        finally:
            transaction.commit()

    def test_requestMirrorPutsBranchInQueue_hosted(self):
        branch = self.makeBranchAndRequestMirror(BranchType.HOSTED)
        self.assertBranchQueues([branch], [], [])

    def test_requestMirrorPutsBranchInQueue_mirrored(self):
        branch = self.makeBranchAndRequestMirror(BranchType.MIRRORED)
        self.assertBranchQueues([], [branch], [])

    def test_requestMirrorPutsBranchInQueue_imported(self):
        branch = self.makeBranchAndRequestMirror(BranchType.IMPORTED)
        self.assertBranchQueues([], [], [branch])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

