# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from unittest import TestLoader

from zope.security.interfaces import Unauthorized

from canonical.database.constants import UTC_NOW
from canonical.testing import DatabaseFunctionalLayer

from lp.code.enums import CodeReviewVote
from lp.code.errors import ClaimReviewFailed
from lp.code.interfaces.codereviewvote import ICodeReviewVoteReference
from lp.testing import login_person, TestCaseWithFactory


class TestCodeReviewVote(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_create_vote(self):
        """CodeReviewVotes can be created"""
        merge_proposal = self.factory.makeBranchMergeProposal()
        reviewer = self.factory.makePerson()
        login_person(merge_proposal.registrant)
        vote = merge_proposal.nominateReviewer(
            reviewer, merge_proposal.registrant)
        self.assertEqual(reviewer, vote.reviewer)
        self.assertEqual(merge_proposal.registrant, vote.registrant)
        self.assertEqual(merge_proposal, vote.branch_merge_proposal)
        self.assertEqual([vote], list(merge_proposal.votes))
        self.assertSqlAttributeEqualsDate(
            vote, 'date_created', UTC_NOW)
        self.assertProvides(vote, ICodeReviewVoteReference)


class TestCodeReviewVoteReferenceClaimReview(TestCaseWithFactory):
    """Tests for CodeReviewVoteReference.claimReview."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        # Setup the proposal, claimant and team reviewer.
        self.bmp = self.factory.makeBranchMergeProposal()
        self.claimant = self.factory.makePerson()
        self.review_team = self.factory.makeTeam()

    def _addPendingReview(self):
        """Add a pending review for the review_team."""
        login_person(self.bmp.registrant)
        return self.bmp.nominateReviewer(
            reviewer=self.review_team,
            registrant=self.bmp.registrant)

    def _addClaimantToReviewTeam(self):
        """Add the claimant to the review team."""
        login_person(self.review_team.teamowner)
        self.review_team.addMember(
            person=self.claimant, reviewer=self.review_team.teamowner)

    def test_personal_completed_review(self):
        # If the claimant has a personal review already, then they can't claim
        # a pending team review.
        login_person(self.claimant)
        # Make sure that the personal review is done before the pending team
        # review, otherwise the pending team review will be claimed by this
        # one.
        self.bmp.createComment(
            self.claimant, 'Message subject', 'Message content',
            vote=CodeReviewVote.APPROVE)
        review = self._addPendingReview()
        self._addClaimantToReviewTeam()
        self.assertRaises(
            ClaimReviewFailed, review.claimReview, self.claimant)

    def test_personal_pending_review(self):
        # If the claimant has a pending review already, then they can't claim
        # a pending team review.
        review = self._addPendingReview()
        self._addClaimantToReviewTeam()
        login_person(self.bmp.registrant)
        self.bmp.nominateReviewer(
            reviewer=self.claimant, registrant=self.bmp.registrant)
        login_person(self.claimant)
        self.assertRaises(
            ClaimReviewFailed, review.claimReview, self.claimant)

    def test_personal_not_in_review_team(self):
        # If the claimant is not in the review team, an error is raised.
        review = self._addPendingReview()
        # Since the claimant isn't in the review team, they don't have
        # launchpad.Edit on the review itself, hence Unauthorized.
        login_person(self.claimant)
        # Actually accessing claimReview triggers the security proxy.
        self.assertRaises(
            Unauthorized, getattr, review, 'claimReview')
        # The merge proposal registrant however does have edit permissions,
        # but isn't in the team, so they get ClaimReviewFailed.
        login_person(self.bmp.registrant)
        self.assertRaises(
            ClaimReviewFailed, review.claimReview, self.bmp.registrant)

    def test_success(self):
        # If the claimant is in the review team, and does not have a personal
        # review, pending or completed, then they can claim the team review.
        review = self._addPendingReview()
        self._addClaimantToReviewTeam()
        login_person(self.claimant)
        review.claimReview(self.claimant)
        self.assertEqual(self.claimant, review.reviewer)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
