# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for CodeReviewVoteReferences."""

__metaclass__ = type


import unittest

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import DatabaseFunctionalLayer
from lp.code.browser.codereviewvote import CodeReviewVoteReassign
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )


class TestReassignReviewer(TestCaseWithFactory):
    """Test functionality for changing the reviewer."""

    layer = DatabaseFunctionalLayer

    def test_reassign(self):
        """A reviewer can reassign their vote to someone else."""
        bmp = self.factory.makeBranchMergeProposal()
        reviewer = self.factory.makePerson()
        login_person(bmp.registrant)
        vote = bmp.nominateReviewer(
            reviewer=reviewer, registrant=bmp.registrant)
        new_reviewer = self.factory.makePerson()
        login_person(reviewer)
        view = CodeReviewVoteReassign(vote, LaunchpadTestRequest())
        view.reassign_action.success({'reviewer': new_reviewer})
        self.assertEqual(vote.reviewer, new_reviewer)

    def test_view_attributes(self):
        """Check various urls etc on view are correct."""
        bmp = self.factory.makeBranchMergeProposal()
        reviewer = self.factory.makePerson()
        login_person(bmp.registrant)
        vote = bmp.nominateReviewer(
            reviewer=reviewer, registrant=bmp.registrant)
        login_person(reviewer)
        view = CodeReviewVoteReassign(vote, LaunchpadTestRequest())
        view.initialize()
        required_cancel_url = (
            "http://code.launchpad.dev/%s/+merge/1"
            % bmp.source_branch.unique_name)
        self.assertEqual(required_cancel_url, view.cancel_url)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
