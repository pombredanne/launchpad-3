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


_default = object()

class TestProposalVoteSummary(TestCaseWithFactory):
    """The vote summary shows a summary of the current votes."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        # Use an admin so we don't have to worry about launchpad.Edit
        # permissions on the merge proposals for adding comments.
        TestCaseWithFactory.setUp(self, user="foo.bar@canonical.com")

    def _createComment(self, proposal, reviewer=None, vote=None,
                       comment=_default):
        """Create a comment on the merge proposal."""
        if reviewer is None:
            reviewer = self.factory.makePerson()
        if comment is _default:
            comment = self.factory.getUniqueString()
        proposal.createComment(
            owner=reviewer,
            subject=self.factory.getUniqueString('subject'),
            content=comment,
            vote=vote)

    def _get_vote_summary(self, proposal):
        """Return the vote summary string for the proposal."""
        view_context = proposal.source_branch.owner
        view = BranchMergeProposalListingView(
            view_context, LaunchpadTestRequest())
        batch_navigator = view.proposals
        # There will only be one item in the list of proposals.
        [listing_item] = batch_navigator.proposals
        return (list(listing_item.vote_summary_items),
                listing_item.comment_count)

    def test_no_votes_or_comments(self):
        # If there are no votes or comments, then we show that.
        proposal = self.factory.makeBranchMergeProposal()
        summary, comment_count = self._get_vote_summary(proposal)
        self.assertEqual([], summary)
        self.assertEqual(0, comment_count)

    def test_no_votes_with_comments(self):
        # The comment count is shown.
        proposal = self.factory.makeBranchMergeProposal()
        self._createComment(proposal)
        summary, comment_count = self._get_vote_summary(proposal)
        self.assertEqual([], summary)
        self.assertEqual(1, comment_count)

    def test_vote_without_comment(self):
        # If there are no comments we don't show a count.
        proposal = self.factory.makeBranchMergeProposal()
        self._createComment(
            proposal, vote=CodeReviewVote.APPROVE, comment=None)
        summary, comment_count = self._get_vote_summary(proposal)
        self.assertEqual(
            [{'name': 'APPROVE', 'title':'Approve', 'count':1,
              'reviewers': ''}],
            summary)
        self.assertEqual(0, comment_count)

    def test_vote_with_comment(self):
        # A vote with a comment counts as a vote and a comment.
        proposal = self.factory.makeBranchMergeProposal()
        self._createComment(proposal, vote=CodeReviewVote.APPROVE)
        summary, comment_count = self._get_vote_summary(proposal)
        self.assertEqual(
            [{'name': 'APPROVE', 'title':'Approve', 'count':1,
              'reviewers': ''}],
            summary)
        self.assertEqual(1, comment_count)

    def test_disapproval(self):
        # Shown as Disapprove: <count>.
        proposal = self.factory.makeBranchMergeProposal()
        self._createComment(proposal, vote=CodeReviewVote.DISAPPROVE)
        summary, comment_count = self._get_vote_summary(proposal)
        self.assertEqual(
            [{'name': 'DISAPPROVE', 'title':'Disapprove', 'count':1,
              'reviewers': ''}],
            summary)
        self.assertEqual(1, comment_count)

    def test_abstain(self):
        # Shown as Abstain: <count>.
        proposal = self.factory.makeBranchMergeProposal()
        self._createComment(proposal, vote=CodeReviewVote.ABSTAIN)
        summary, comment_count = self._get_vote_summary(proposal)
        self.assertEqual(
            [{'name': 'ABSTAIN', 'title':'Abstain', 'count':1,
              'reviewers': ''}],
            summary)
        self.assertEqual(1, comment_count)

    def test_vote_ranking(self):
        # Votes go from best to worst.
        proposal = self.factory.makeBranchMergeProposal()
        self._createComment(proposal, vote=CodeReviewVote.DISAPPROVE)
        self._createComment(proposal, vote=CodeReviewVote.APPROVE)
        summary, comment_count = self._get_vote_summary(proposal)
        self.assertEqual(
            [{'name': 'APPROVE', 'title':'Approve', 'count':1,
              'reviewers': ''},
             {'name': 'DISAPPROVE', 'title':'Disapprove', 'count':1,
              'reviewers': ''}],
            summary)
        self.assertEqual(2, comment_count)
        self._createComment(proposal, vote=CodeReviewVote.ABSTAIN)
        summary, comment_count = self._get_vote_summary(proposal)
        self.assertEqual(
            [{'name': 'APPROVE', 'title':'Approve', 'count':1,
              'reviewers': ''},
             {'name': 'ABSTAIN', 'title':'Abstain', 'count':1,
              'reviewers': ''},
             {'name': 'DISAPPROVE', 'title':'Disapprove', 'count':1,
              'reviewers': ''}],
            summary)
        self.assertEqual(3, comment_count)

    def test_multiple_votes_for_type(self):
        # Multiple votes of a type are aggregated in the summary.
        proposal = self.factory.makeBranchMergeProposal()
        self._createComment(proposal, vote=CodeReviewVote.DISAPPROVE)
        self._createComment(proposal, vote=CodeReviewVote.APPROVE)
        self._createComment(proposal, vote=CodeReviewVote.DISAPPROVE)
        self._createComment(proposal, vote=CodeReviewVote.APPROVE)
        self._createComment(
            proposal, vote=CodeReviewVote.ABSTAIN, comment=None)
        self._createComment(
            proposal, vote=CodeReviewVote.APPROVE, comment=None)
        summary, comment_count = self._get_vote_summary(proposal)
        self.assertEqual(
            [{'name': 'APPROVE', 'title':'Approve', 'count':3,
              'reviewers': ''},
             {'name': 'ABSTAIN', 'title':'Abstain', 'count':1,
              'reviewers': ''},
             {'name': 'DISAPPROVE', 'title':'Disapprove', 'count':2,
              'reviewers': ''}],
            summary)
        self.assertEqual(4, comment_count)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
