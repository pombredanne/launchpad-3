# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for BranchMergeProposal listing views."""

__metaclass__ = type

from unittest import TestLoader

import transaction

from lp.code.browser.branchmergeproposallisting import (
    BranchMergeProposalListingView, ProductActiveReviewsView)
from lp.code.interfaces.codereviewcomment import (
    CodeReviewVote)
from canonical.launchpad.testing import (
    ANONYMOUS, login, login_person, TestCaseWithFactory)
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import DatabaseFunctionalLayer

_default = object()

class TestProposalVoteSummary(TestCaseWithFactory):
    """The vote summary shows a summary of the current votes."""

    layer = DatabaseFunctionalLayer

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
        transaction.commit()
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


class TestProductActiveReviewGroups(TestCaseWithFactory):
    """Tests for groupings used in for active reviews."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.bmp = self.factory.makeBranchMergeProposal()

    def assertReviewGroupForUser(self, user, group):
        # Assert that the group for the user is correct.
        if user is None:
            login(ANONYMOUS)
        else:
            login_person(user)
        view = ProductActiveReviewsView(
            self.bmp.target_branch.product, LaunchpadTestRequest())
        self.assertEqual(
            group, view._getReviewGroup(self.bmp, self.bmp.votes))

    def test_not_logged_in(self):
        # If there is no logged in user, then the group is other.
        self.assertReviewGroupForUser(None, ProductActiveReviewsView.OTHER)

    def test_source_branch_owner(self):
        # If the logged in user is the owner of the source branch,
        # then the review is MINE.
        self.assertReviewGroupForUser(
            self.bmp.source_branch.owner, ProductActiveReviewsView.MINE)

    def test_proposal_registrant(self):
        # If the logged in user it the registrant of the proposal, then it is
        # MINE only if the registrant is a member of the team that owns the
        # branch.
        self.assertReviewGroupForUser(
            self.bmp.registrant, ProductActiveReviewsView.OTHER)
        team = self.factory.makeTeam(self.bmp.registrant)
        login_person(self.bmp.source_branch.owner)
        self.bmp.source_branch.owner = team
        self.assertReviewGroupForUser(
            self.bmp.registrant, ProductActiveReviewsView.MINE)

    def test_target_branch_owner(self):
        # For other people, even the target branch owner, it is other.
        self.assertReviewGroupForUser(
            self.bmp.target_branch.owner, ProductActiveReviewsView.OTHER)

    def test_group_pending_review(self):
        # If the logged in user has a pending review request, it is a TO_DO.
        reviewer = self.factory.makePerson()
        login_person(self.bmp.registrant)
        self.bmp.nominateReviewer(reviewer, self.bmp.registrant)
        self.assertReviewGroupForUser(
            reviewer, ProductActiveReviewsView.TO_DO)

    def test_group_pending_team_review(self):
        # If the logged in user of a team that has a pending review request,
        # it is a CAN_DO.
        reviewer = self.factory.makePerson()
        login_person(self.bmp.registrant)
        team = self.factory.makeTeam(reviewer)
        self.bmp.nominateReviewer(team, self.bmp.registrant)
        self.assertReviewGroupForUser(
            reviewer, ProductActiveReviewsView.CAN_DO)

    def test_review_done(self):
        # If the logged in user has a completed review, then the review is
        # ARE_DOING.
        reviewer = self.bmp.target_branch.owner
        login_person(reviewer)
        self.bmp.createComment(
            reviewer, 'subject', vote=CodeReviewVote.APPROVE)
        self.assertReviewGroupForUser(
            reviewer, ProductActiveReviewsView.ARE_DOING)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
