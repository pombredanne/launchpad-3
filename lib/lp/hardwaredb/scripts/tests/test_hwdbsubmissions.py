# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for hwdbsubmissions script."""

__metaclass__ = type


from canonical.testing.layers import LaunchpadScriptLayer
from lp.hardwaredb.interfaces.hwdb import HWSubmissionProcessingStatus
from lp.hardwaredb.scripts.hwdbsubmissions import (
    ProcessingLoopForPendingSubmissions,
    ProcessingLoopForReprocessingBadSubmissions,
    )
from lp.testing import TestCaseWithFactory


class TestProcessingLoops(TestCaseWithFactory):
    layer = LaunchpadScriptLayer

    def _makePendingSubmissionsLoop(self):
        """Parameters don't matter for these tests."""
        return ProcessingLoopForPendingSubmissions(None, None, 0, False)

    def test_PendingSubmissions_submitted_found(self):
        # The PendingSubmissions loop finds submitted entries.
        submission = self.factory.makeHWSubmission(
            status=HWSubmissionProcessingStatus.SUBMITTED)
        loop = self._makePendingSubmissionsLoop()
        # The sample data already contains one submission which we ignore.
        submissions = loop.getUnprocessedSubmissions(2)
        self.assertEqual([submission], submissions[1:])

    def test_PendingSubmissions_processed_not_found(self):
        # The PendingSubmissions loop ignores processed entries.
        submission = self.factory.makeHWSubmission(
            status=HWSubmissionProcessingStatus.PROCESSED)
        loop = self._makePendingSubmissionsLoop()
        # The sample data already contains one submission which we ignore.
        submissions = loop.getUnprocessedSubmissions(2)
        self.assertEqual([], submissions[1:])
        self.assertNotEqual([submission], submissions)

    def test_PendingSubmissions_invalid_not_found(self):
        # The PendingSubmissions loop ignores invalid entries.
        submission = self.factory.makeHWSubmission(
            status=HWSubmissionProcessingStatus.INVALID)
        loop = self._makePendingSubmissionsLoop()
        # The sample data already contains one submission which we ignore.
        submissions = loop.getUnprocessedSubmissions(2)
        self.assertEqual([], submissions[1:])
        self.assertNotEqual([submission], submissions)

    def test_PendingSubmissions_respects_chunk_size(self):
        # Only the requested number of entries are returned.
        self.factory.makeHWSubmission(
            status=HWSubmissionProcessingStatus.SUBMITTED)
        self.factory.makeHWSubmission(
            status=HWSubmissionProcessingStatus.SUBMITTED)
        loop = self._makePendingSubmissionsLoop()
        # The sample data already contains one submission.
        submissions = loop.getUnprocessedSubmissions(2)
        self.assertEqual(2, len(submissions))

    def _makeBadSubmissionsLoop(self, start=0):
        """Parameters don't matter for these tests."""
        return ProcessingLoopForReprocessingBadSubmissions(
            start, None, None, 0, False)

    def test_BadSubmissions_invalid_found(self):
        # The BadSubmissions loop finds invalid entries.
        submission = self.factory.makeHWSubmission(
            status=HWSubmissionProcessingStatus.INVALID)
        loop = self._makeBadSubmissionsLoop()
        submissions = loop.getUnprocessedSubmissions(2)
        self.assertEqual([submission], submissions)

    def test_BadSubmissions_processed_not_found(self):
        # The BadSubmissions loop ignores processed entries.
        self.factory.makeHWSubmission(
            status=HWSubmissionProcessingStatus.PROCESSED)
        loop = self._makeBadSubmissionsLoop()
        submissions = loop.getUnprocessedSubmissions(2)
        self.assertEqual([], submissions)

    def test_BadSubmissions_submitted_not_found(self):
        # The BadSubmissions loop ignores submitted entries.
        self.factory.makeHWSubmission(
            status=HWSubmissionProcessingStatus.SUBMITTED)
        loop = self._makeBadSubmissionsLoop()
        submissions = loop.getUnprocessedSubmissions(2)
        self.assertEqual([], submissions)

    def test_BadSubmissions_respects_chunk_size(self):
        # Only the requested number of entries are returned.
        self.factory.makeHWSubmission(
            status=HWSubmissionProcessingStatus.INVALID)
        self.factory.makeHWSubmission(
            status=HWSubmissionProcessingStatus.INVALID)
        loop = self._makeBadSubmissionsLoop()
        # The sample data already contains one submission.
        submissions = loop.getUnprocessedSubmissions(1)
        self.assertEqual(1, len(submissions))

    def test_BadSubmissions_respects_start(self):
        # It is possible to request a start id. Previous entries are ignored.
        submission1 = self.factory.makeHWSubmission(
            status=HWSubmissionProcessingStatus.INVALID)
        submission2 = self.factory.makeHWSubmission(
            status=HWSubmissionProcessingStatus.INVALID)
        self.assertTrue(submission1.id < submission2.id)
        loop = self._makeBadSubmissionsLoop(submission2.id)
        # The sample data already contains one submission.
        submissions = loop.getUnprocessedSubmissions(2)
        self.assertEqual([submission2], submissions)
