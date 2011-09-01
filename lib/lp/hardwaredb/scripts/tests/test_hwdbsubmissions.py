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
        # The sample data already contains one
        submissions = loop.getUnprocessedSubmissions(2)
        self.assertEqual([submission], submissions[1:])
