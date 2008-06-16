# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for BranchMergeProposal listing views."""

__metaclass__ = type

from unittest import TestLoader

from canonical.launchpad.browser.branchmergeproposallisting import (
    BranchMergeProposalListingView)
from canonical.launchpad.interfaces.codereviewcomment import (
    CodeReviewVote)
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import LaunchpadFunctionalLayer


class TestProposalVoteSummary(TestCaseWithFactory):
    """The vote summary shows a summary of the current votes."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        # Use an admin so we don't have to worry about launchpad.Edit
        # permissions on the merge proposals for adding comments.
        TestCaseWithFactory.setUp(self, user="foo.bar@canonical.com")

    def _createComment(self, proposal, reviewer=None, vote=None):
        """Create a comment on the merge proposal."""
        if reviewer is None:
            reviewer = self.factory.makePerson()
        proposal.createComment(
            owner=reviewer,
            subject=self.factory.getUniqueString('subject'),
            vote=vote)

    def _get_vote_summary(self, proposal):
        """Return the vote summary string for the proposal."""
        view_context = proposal.source_branch.owner
        view = BranchMergeProposalListingView(
            view_context, LaunchpadTestRequest())
        batch_navigator = view.proposals
        listing_items = batch_navigator.proposals
        self.assertEqual(1, len(listing_items))
        return listing_items[0].vote_summary

    def test_no_votes_or_comments(self):
        # If there are no votes or comments, then we show that.
        proposal = self.factory.makeBranchMergeProposal()
        self.assertEqual(
            'no votes (no comments)',
            self._get_vote_summary(proposal))

    def test_no_votes_with_comments(self):
        # The comment count is shown, but the vote section still shows
        # "no votes".
        proposal = self.factory.makeBranchMergeProposal()
        self._createComment(proposal)
        self.assertEqual(
            'no votes (Comments: 1)',
            self._get_vote_summary(proposal))

    def test_disapproval(self):
        # Shown as Disapprove: <count>.
        proposal = self.factory.makeBranchMergeProposal()
        self._createComment(proposal, vote=CodeReviewVote.DISAPPROVE)
        self.assertEqual(
            'Disapprove: 1 (Comments: 1)',
            self._get_vote_summary(proposal))

    def test_approval(self):
        # Shown as Approve: <count>.
        proposal = self.factory.makeBranchMergeProposal()
        self._createComment(proposal, vote=CodeReviewVote.APPROVE)
        self.assertEqual(
            'Approve: 1 (Comments: 1)',
            self._get_vote_summary(proposal))

    def test_abstain(self):
        # Shown as Abstain: <count>.
        proposal = self.factory.makeBranchMergeProposal()
        self._createComment(proposal, vote=CodeReviewVote.ABSTAIN)
        self.assertEqual(
            'Abstain: 1 (Comments: 1)',
            self._get_vote_summary(proposal))

    def test_disapprove_first(self):
        # Disapprovals come first in the summary.
        proposal = self.factory.makeBranchMergeProposal()
        self._createComment(proposal, vote=CodeReviewVote.DISAPPROVE)
        self._createComment(proposal, vote=CodeReviewVote.APPROVE)
        self.assertEqual(
            'Disapprove: 1, Approve: 1 (Comments: 2)',
            self._get_vote_summary(proposal))
        self._createComment(proposal, vote=CodeReviewVote.ABSTAIN)
        self.assertEqual(
            'Disapprove: 1, Approve: 1, Abstain: 1 (Comments: 3)',
            self._get_vote_summary(proposal))

    def test_approve_before_abstain(self):
        # If the only vote types are approve and abstain, then the approve
        # count comes first.
        proposal = self.factory.makeBranchMergeProposal()
        self._createComment(proposal, vote=CodeReviewVote.APPROVE)
        self._createComment(proposal, vote=CodeReviewVote.ABSTAIN)
        self.assertEqual(
            'Approve: 1, Abstain: 1 (Comments: 2)',
            self._get_vote_summary(proposal))

    def test_multiple_votes_for_type(self):
        # Multiple votes of a type are aggregated in the summary.
        proposal = self.factory.makeBranchMergeProposal()
        self._createComment(proposal, vote=CodeReviewVote.DISAPPROVE)
        self._createComment(proposal, vote=CodeReviewVote.APPROVE)
        self._createComment(proposal, vote=CodeReviewVote.DISAPPROVE)
        self._createComment(proposal, vote=CodeReviewVote.APPROVE)
        self._createComment(proposal, vote=CodeReviewVote.ABSTAIN)
        self._createComment(proposal, vote=CodeReviewVote.APPROVE)
        self.assertEqual(
            'Disapprove: 2, Approve: 3, Abstain: 1 (Comments: 6)',
            self._get_vote_summary(proposal))


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
