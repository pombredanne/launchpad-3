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
        return listing_item.vote_summary

    def test_no_votes_or_comments(self):
        # If there are no votes or comments, then we show that.
        proposal = self.factory.makeBranchMergeProposal()
        self.assertEqual(
            '<em>None</em>',
            self._get_vote_summary(proposal))

    def test_no_votes_with_comments(self):
        # The comment count is shown.
        proposal = self.factory.makeBranchMergeProposal()
        self._createComment(proposal)
        # XXX: rockstar - 9 Oct 2009 - HTML in python is bad. See bug #281063.
        self.assertEqual(
            'Comments:&nbsp;1',
            self._get_vote_summary(proposal))

    def test_vote_without_comment(self):
        # If there are no comments we don't show a count.
        proposal = self.factory.makeBranchMergeProposal()
        self._createComment(
            proposal, vote=CodeReviewVote.APPROVE, comment=None)
        # XXX: rockstar - 9 Oct 2009 - HTML in python is bad. See bug #281063.
        self.assertEqual(
            '<span class="voteAPPROVE">Approve:&nbsp;1</span>',
            self._get_vote_summary(proposal))

    def test_vote_with_comment(self):
        # A vote with a comment counts as a vote and a comment.
        proposal = self.factory.makeBranchMergeProposal()
        self._createComment(proposal, vote=CodeReviewVote.APPROVE)
        # XXX: rockstar - 9 Oct 2009 - HTML in python is bad. See bug #281063.
        self.assertEqual(
            '<span class="voteAPPROVE">Approve:&nbsp;1</span>, '
            'Comments:&nbsp;1',
            self._get_vote_summary(proposal))

    def test_disapproval(self):
        # Shown as Disapprove: <count>.
        proposal = self.factory.makeBranchMergeProposal()
        self._createComment(proposal, vote=CodeReviewVote.DISAPPROVE)
        # XXX: rockstar - 9 Oct 2009 - HTML in python is bad. See bug #281063.
        self.assertEqual(
            '<span class="voteDISAPPROVE">Disapprove:&nbsp;1</span>, '
            'Comments:&nbsp;1',
            self._get_vote_summary(proposal))

    def test_abstain(self):
        # Shown as Abstain: <count>.
        proposal = self.factory.makeBranchMergeProposal()
        self._createComment(proposal, vote=CodeReviewVote.ABSTAIN)
        # XXX: rockstar - 9 Oct 2009 - HTML in python is bad. See bug #281063.
        self.assertEqual(
            '<span class="voteABSTAIN">Abstain:&nbsp;1</span>, '
            'Comments:&nbsp;1',
            self._get_vote_summary(proposal))

    def test_vote_ranking(self):
        # Votes go from best to worst.
        proposal = self.factory.makeBranchMergeProposal()
        self._createComment(proposal, vote=CodeReviewVote.DISAPPROVE)
        self._createComment(proposal, vote=CodeReviewVote.APPROVE)
        # XXX: rockstar - 9 Oct 2009 - HTML in python is bad. See bug #281063.
        self.assertEqual(
            '<span class="voteAPPROVE">Approve:&nbsp;1</span>, '
            '<span class="voteDISAPPROVE">Disapprove:&nbsp;1</span>, '
            'Comments:&nbsp;2',
            self._get_vote_summary(proposal))
        self._createComment(proposal, vote=CodeReviewVote.ABSTAIN)
        self.assertEqual(
            '<span class="voteAPPROVE">Approve:&nbsp;1</span>, '
            '<span class="voteABSTAIN">Abstain:&nbsp;1</span>, '
            '<span class="voteDISAPPROVE">Disapprove:&nbsp;1</span>, '
            'Comments:&nbsp;3',
            self._get_vote_summary(proposal))

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
        # XXX: rockstar - 9 Oct 2009 - HTML in python is bad. See bug #281063.
        self.assertEqual(
            '<span class="voteAPPROVE">Approve:&nbsp;3</span>, '
            '<span class="voteABSTAIN">Abstain:&nbsp;1</span>, '
            '<span class="voteDISAPPROVE">Disapprove:&nbsp;2</span>, '
            'Comments:&nbsp;4',
            self._get_vote_summary(proposal))


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
