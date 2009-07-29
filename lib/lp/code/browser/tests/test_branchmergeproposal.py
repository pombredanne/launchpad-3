# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=F0401

"""Unit tests for BranchMergeProposals."""

__metaclass__ = type

from datetime import timedelta
import unittest

import transaction
from zope.component import getMultiAdapter
from zope.security.interfaces import Unauthorized

from lp.code.browser.branch import RegisterBranchMergeProposalView
from lp.code.browser.branchmergeproposal import (
    BranchMergeProposalAddVoteView, BranchMergeProposalChangeStatusView,
    BranchMergeProposalMergedView, BranchMergeProposalView,
    BranchMergeProposalVoteView)
from lp.code.enums import BranchMergeProposalStatus, CodeReviewVote
from lp.testing import (
    login_person, TestCaseWithFactory, time_counter)
from lp.code.model.diff import StaticDiff
from canonical.launchpad.webapp.interfaces import IPrimaryContext
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import (
    DatabaseFunctionalLayer, LaunchpadFunctionalLayer)


class TestBranchMergeProposalPrimaryContext(TestCaseWithFactory):
    """Tests the adaptation of a merge proposal into a primary context."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Use an admin so we don't have to worry about launchpad.Edit
        # permissions on the merge proposals.
        TestCaseWithFactory.setUp(self, user="admin@canonical.com")

    def testPrimaryContext(self):
        # The primary context of a merge proposal is the same as the primary
        # context of the source_branch.
        bmp = self.factory.makeBranchMergeProposal()
        self.assertEqual(
            IPrimaryContext(bmp).context,
            IPrimaryContext(bmp.source_branch).context)


class TestBranchMergeProposalMergedView(TestCaseWithFactory):
    """Tests for `BranchMergeProposalMergedView`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Use an admin so we don't have to worry about launchpad.Edit
        # permissions on the merge proposals for adding comments, or
        # nominating reviewers.
        TestCaseWithFactory.setUp(self, user="admin@canonical.com")
        self.bmp = self.factory.makeBranchMergeProposal()

    def test_initial_values(self):
        # The default merged_revno is the head revno of the target branch.
        view = BranchMergeProposalMergedView(self.bmp, LaunchpadTestRequest())
        self.bmp.source_branch.revision_count = 1
        self.bmp.target_branch.revision_count = 2
        self.assertEqual(
            {'merged_revno': self.bmp.target_branch.revision_count},
            view.initial_values)


class TestBranchMergeProposalAddVoteView(TestCaseWithFactory):
    """Test the AddVote view."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.bmp = self.factory.makeBranchMergeProposal()

    def _createView(self):
        # Construct the view and initialize it.
        view = BranchMergeProposalAddVoteView(
            self.bmp, LaunchpadTestRequest())
        view.initialize()
        return view

    def test_init_with_random_person(self):
        """Any random person ought to be able to vote."""
        login_person(self.factory.makePerson())
        self._createView()

    def test_init_with_anonymous(self):
        """Anonymous people cannot vote."""
        self.assertRaises(AssertionError, self._createView)


class TestBranchMergeProposalVoteView(TestCaseWithFactory):
    """Make sure that the votes are returned in the right order."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Use an admin so we don't have to worry about launchpad.Edit
        # permissions on the merge proposals for adding comments, or
        # nominating reviewers.
        TestCaseWithFactory.setUp(self, user="admin@canonical.com")
        self.bmp = self.factory.makeBranchMergeProposal()
        self.date_generator = time_counter(delta=timedelta(days=1))

    def _createComment(self, reviewer, vote):
        """Create a comment on the merge proposal."""
        self.bmp.createComment(
            owner=reviewer,
            subject=self.factory.getUniqueString('subject'),
            vote=vote,
            _date_created=self.date_generator.next())

    def _nominateReviewer(self, reviewer, registrant):
        """Nominate a reviewer for the merge proposal."""
        self.bmp.nominateReviewer(
            reviewer=reviewer, registrant=registrant,
            _date_created=self.date_generator.next())

    def testNoVotes(self):
        # No votes should return empty lists
        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())
        self.assertEqual([], view.current_reviews)
        self.assertEqual([], view.requested_reviews)

    def testRequestedOrdering(self):
        # No votes should return empty lists
        # Request three reviews.
        albert = self.factory.makePerson(name='albert')
        bob = self.factory.makePerson(name='bob')
        charles = self.factory.makePerson(name='charles')

        owner = self.bmp.source_branch.owner

        self._nominateReviewer(albert, owner)
        self._nominateReviewer(bob, owner)
        self._nominateReviewer(charles, owner)

        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())
        self.assertEqual([], view.current_reviews)
        requested_reviews = view.requested_reviews
        self.assertEqual(3, len(requested_reviews))
        self.assertEqual(
            [charles, bob, albert],
            [review.reviewer for review in requested_reviews])

    def test_user_can_claim_self(self):
        """Someone cannot claim a review already assigned to them."""
        albert = self.factory.makePerson()
        owner = self.bmp.source_branch.owner
        self._nominateReviewer(albert, owner)
        login_person(albert)
        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())
        self.assertFalse(view.requested_reviews[0].user_can_claim)

    def test_user_can_claim_member(self):
        """Someone can claim a review already assigned their team."""
        albert = self.factory.makePerson()
        review_team = self.factory.makeTeam()
        albert.join(review_team)
        owner = self.bmp.source_branch.owner
        self._nominateReviewer(review_team, owner)
        login_person(albert)
        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())
        self.assertTrue(view.requested_reviews[0].user_can_claim)

    def test_user_can_claim_nonmember(self):
        """A non-member cannot claim a team's review."""
        albert = self.factory.makePerson()
        review_team = self.factory.makeTeam()
        owner = self.bmp.source_branch.owner
        self._nominateReviewer(review_team, owner)
        login_person(albert)
        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())
        self.assertFalse(view.requested_reviews[0].user_can_claim)

    def testCurrentReviewOrdering(self):
        # Most recent first.
        # Request three reviews.
        albert = self.factory.makePerson(name='albert')
        bob = self.factory.makePerson(name='bob')
        charles = self.factory.makePerson(name='charles')

        owner = self.bmp.source_branch.owner

        self._createComment(albert, CodeReviewVote.APPROVE)
        self._createComment(bob, CodeReviewVote.ABSTAIN)
        self._createComment(charles, CodeReviewVote.DISAPPROVE)

        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())

        self.assertEqual(
            [charles, bob, albert],
            [review.reviewer for review in view.current_reviews])

    def testChangeOfVoteBringsToTop(self):
        # Changing the vote changes the vote date, so it comes to the top.
        # Request three reviews.
        albert = self.factory.makePerson(name='albert')
        bob = self.factory.makePerson(name='bob')

        owner = self.bmp.source_branch.owner

        self._createComment(albert, CodeReviewVote.ABSTAIN)
        self._createComment(bob, CodeReviewVote.APPROVE)
        self._createComment(albert, CodeReviewVote.APPROVE)

        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())

        self.assertEqual(
            [albert, bob],
            [review.reviewer for review in view.current_reviews])

    def addReviewTeam(self):
        review_team = self.factory.makeTeam(name='reviewteam')
        target_branch = self.factory.makeAnyBranch()
        self.bmp.target_branch.reviewer = review_team

    def test_review_team_members_trusted(self):
        """Members of the target branch's review team are trusted."""
        self.addReviewTeam()
        albert = self.factory.makePerson(name='albert')
        albert.join(self.bmp.target_branch.reviewer)
        self._createComment(albert, CodeReviewVote.APPROVE)
        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())
        self.assertTrue(view.reviews[0].trusted)

    def test_review_team_nonmembers_untrusted(self):
        """Non-members of the target branch's review team are untrusted."""
        self.addReviewTeam()
        albert = self.factory.makePerson(name='albert')
        self._createComment(albert, CodeReviewVote.APPROVE)
        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())
        self.assertFalse(view.reviews[0].trusted)

    def test_no_review_team_untrusted(self):
        """If the target branch has no review team, everyone is untrusted."""
        albert = self.factory.makePerson(name='albert')
        self._createComment(albert, CodeReviewVote.APPROVE)
        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())
        self.assertFalse(view.reviews[0].trusted)

    def test_render_all_vote_types(self):
        # A smoke test that the view knows how to render all types of vote.
        for vote in CodeReviewVote.items:
            self._createComment(
                self.factory.makePerson(), vote)

        view = getMultiAdapter(
            (self.bmp, LaunchpadTestRequest()), name='+votes')
        self.failUnless(
            isinstance(view, BranchMergeProposalVoteView),
            "The +votes page for a BranchMergeProposal is expected to be a "
            "BranchMergeProposalVoteView")
        # We just test that rendering does not raise.
        view.render()


class TestRegisterBranchMergeProposalView(TestCaseWithFactory):
    """Test the merge proposal registration view."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.target_branch = self.factory.makeProductBranch()
        self.source_branch = self.factory.makeProductBranch(
            product=self.target_branch.product)
        self.user = self.factory.makePerson()
        login_person(self.user)

    def _createView(self):
        # Construct the view and initialize it.
        view = RegisterBranchMergeProposalView(
            self.source_branch, LaunchpadTestRequest())
        view.initialize()
        return view

    def _getSourceProposal(self):
        # There will only be one proposal and it will be in needs review
        # state.
        landing_targets = list(self.source_branch.landing_targets)
        self.assertEqual(1, len(landing_targets))
        proposal = landing_targets[0]
        self.assertEqual(self.target_branch, proposal.target_branch)
        self.assertEqual(BranchMergeProposalStatus.NEEDS_REVIEW,
                         proposal.queue_status)
        return proposal

    def assertNoComments(self, proposal):
        # There should be no comments.
        self.assertEqual([], list(proposal.all_comments))

    def assertOneComment(self, proposal, comment_text):
        # There should be one and only one comment with the text specified.
        self.assertEqual(
            [comment_text],
            [comment.message.text_contents
             for comment in proposal.all_comments])

    def assertNoPendingReviews(self, proposal):
        # There should be no votes recorded for the proposal.
        self.assertEqual([], list(proposal.votes))

    def assertOnePendingReview(self, proposal, reviewer, review_type=None):
        # There should be one pending vote for the reviewer with the specified
        # review type.
        votes = list(proposal.votes)
        self.assertEqual(1, len(votes))
        self.assertEqual(reviewer, votes[0].reviewer)
        self.assertEqual(self.user, votes[0].registrant)
        self.assertIs(None, votes[0].comment)
        if review_type is None:
            self.assertIs(None, votes[0].review_type)
        else:
            self.assertEqual(review_type, votes[0].review_type)

    def test_register_simplest_case(self):
        # This simplest case is where the user only specifies the target
        # branch, and not an initial comment or reviewer.
        view = self._createView()
        view.register_action.success({'target_branch': self.target_branch})
        proposal = self._getSourceProposal()
        self.assertNoPendingReviews(proposal)
        self.assertNoComments(proposal)

    def test_register_initial_comment(self):
        # If the user specifies an initial comment, this is added to the
        # proposal.
        view = self._createView()
        view.register_action.success(
            {'target_branch': self.target_branch,
             'comment': "This is the first comment."})

        proposal = self._getSourceProposal()
        self.assertNoPendingReviews(proposal)
        self.assertOneComment(proposal, "This is the first comment.")

    def test_register_request_reviewer(self):
        # If the user requests a reviewer, then a pending vote is added to the
        # proposal.
        reviewer = self.factory.makePerson()
        view = self._createView()
        view.register_action.success(
            {'target_branch': self.target_branch,
             'reviewer': reviewer})

        proposal = self._getSourceProposal()
        self.assertOnePendingReview(proposal, reviewer)
        self.assertNoComments(proposal)

    def test_register_request_review_type(self):
        # We can request a specific review type of the reviewer.  If we do, it
        # is recorded along with the pending review.
        reviewer = self.factory.makePerson()
        view = self._createView()
        view.register_action.success(
            {'target_branch': self.target_branch,
             'reviewer': reviewer,
             'review_type': 'god-like'})

        proposal = self._getSourceProposal()
        self.assertOnePendingReview(proposal, reviewer, 'god-like')
        self.assertNoComments(proposal)

    def test_register_comment_and_review(self):
        # The user can give an initial comment and request a review from
        # someone.
        reviewer = self.factory.makePerson()
        view = self._createView()
        view.register_action.success(
            {'target_branch': self.target_branch,
             'reviewer': reviewer,
             'review_type': 'god-like',
             'comment': "This is the first comment."})

        proposal = self._getSourceProposal()
        self.assertOnePendingReview(proposal, reviewer, 'god-like')
        self.assertOneComment(proposal, "This is the first comment.")


class TestBranchMergeProposalView(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.user = self.factory.makePerson()
        self.bmp = self.factory.makeBranchMergeProposal(registrant=self.user)
        login_person(self.user)

    def _createView(self):
        # Construct the view and initialize it.
        view = BranchMergeProposalView(
            self.bmp, LaunchpadTestRequest())
        view.initialize()
        return view

    def makeTeamReview(self):
        owner = self.bmp.source_branch.owner
        review_team = self.factory.makeTeam()
        return self.bmp.nominateReviewer(review_team, owner)

    def test_claim_action_team_member(self):
        """Claiming a review works for members of the requested team."""
        review = self.makeTeamReview()
        albert = self.factory.makePerson()
        albert.join(review.reviewer)
        login_person(albert)
        view = self._createView()
        view.claim_action.success({'review_id': review.id})
        self.assertEqual(albert, review.reviewer)

    def test_claim_action_non_member(self):
        """Claiming a review does not work for non-members."""
        review = self.makeTeamReview()
        albert = self.factory.makePerson()
        login_person(albert)
        view = self._createView()
        self.assertRaises(Unauthorized, view.claim_action.success,
                          {'review_id': review.id})

    def test_review_diff_with_no_diff(self):
        """review_diff should be None when there is no context.review_diff."""
        view = self._createView()
        self.assertIs(None, view.review_diff)

    def test_review_diff_utf8(self):
        """A review_diff in utf-8 should be converted to utf-8."""
        text = ''.join(unichr(x) for x in range(255))
        diff = StaticDiff.acquireFromText('x', 'y', text.encode('utf-8'))
        transaction.commit()
        self.bmp.review_diff = diff
        self.assertEqual(text, self._createView().review_diff)

    def test_review_diff_all_chars(self):
        """review_diff should work on diffs containing all possible bytes."""
        text = ''.join(chr(x) for x in range(255))
        diff = StaticDiff.acquireFromText('x', 'y', text)
        transaction.commit()
        self.bmp.review_diff = diff
        self.assertEqual(text.decode('windows-1252', 'replace'),
                         self._createView().review_diff)


class TestBranchMergeProposalChangeStatusOptions(TestCaseWithFactory):
    """Test the status vocabulary generated for then +edit-status view."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.user = self.factory.makePerson()
        login_person(self.user)
        self.proposal = self.factory.makeBranchMergeProposal(
            registrant=self.user)

    def _createView(self):
        # Construct the view and initialize it.
        view = BranchMergeProposalChangeStatusView(
            self.proposal, LaunchpadTestRequest())
        view.initialize()
        return view

    def assertStatusVocabTokens(self, tokens, user):
        # Assert that the tokens specified are the only tokens in the
        # generated vocabulary.
        login_person(user)
        vocabulary = self._createView()._createStatusVocabulary()
        vocab_tokens = sorted([term.token for term in vocabulary])
        self.assertEqual(
            sorted(tokens), vocab_tokens)

    def assertAllStatusesAvailable(self, user, except_for=None):
        # All options should be available to the user.
        desired_statuses = set([
            'WORK_IN_PROGRESS', 'NEEDS_REVIEW', 'MERGED', 'CODE_APPROVED',
            'REJECTED', 'SUPERSEDED'])
        if except_for is not None:
            desired_statuses -= set(except_for)
        self.assertStatusVocabTokens(desired_statuses, user)

    def test_createStatusVocabulary_non_reviewer(self):
        # Neither the source branch owner nor the registrant should be
        # able to approve or reject their own code (assuming they don't have
        # rights on the target branch).
        status_options = [
            'WORK_IN_PROGRESS', 'NEEDS_REVIEW', 'MERGED', 'SUPERSEDED']
        self.assertStatusVocabTokens(
            status_options, user=self.proposal.source_branch.owner)
        self.assertStatusVocabTokens(
            status_options, user=self.proposal.registrant)

    def test_createStatusVocabulary_reviewer(self):
        # The registrant should not be able to approve or reject
        # their own code (assuming they don't have rights on the target
        # branch).
        self.assertAllStatusesAvailable(self.proposal.target_branch.owner)

    def test_createStatusVocabulary_non_reviewer_approved(self):
        # Once the branch has been approved, the source owner or the
        # registrant can queue the branch.
        self.proposal.approveBranch(
            self.proposal.target_branch.owner, 'some-revision')
        status_options = [
            'WORK_IN_PROGRESS', 'NEEDS_REVIEW', 'CODE_APPROVED', 'MERGED',
            'SUPERSEDED']
        self.assertStatusVocabTokens(
            status_options, user=self.proposal.source_branch.owner)
        self.assertStatusVocabTokens(
            status_options, user=self.proposal.registrant)

    def test_createStatusVocabulary_reviewer_approved(self):
        # The target branch owner's options are not changed by whether or not
        # the proposal is currently approved.
        self.proposal.approveBranch(
            self.proposal.target_branch.owner, 'some-revision')
        self.assertAllStatusesAvailable(
            user=self.proposal.target_branch.owner)

    def test_createStatusVocabulary_rejected(self):
        # Only reviewers can change rejected proposals to approved.  All other
        # options for rejected proposals are the same regardless of user.
        self.proposal.rejectBranch(
            self.proposal.target_branch.owner, 'some-revision')
        self.assertAllStatusesAvailable(
            user=self.proposal.source_branch.owner,
            except_for=['CODE_APPROVED', 'QUEUED'])
        self.assertAllStatusesAvailable(user=self.proposal.registrant,
            except_for=['CODE_APPROVED', 'QUEUED'])
        self.assertAllStatusesAvailable(
            user=self.proposal.target_branch.owner)

    def test_createStatusVocabulary_queued(self):
        # Queued proposals can go to any status, but only reviewers can set
        # them to REJECTED.
        self.proposal.enqueue(
            self.proposal.target_branch.owner, 'some-revision')

        self.assertAllStatusesAvailable(
            user=self.proposal.source_branch.owner, except_for=['REJECTED'])
        self.assertAllStatusesAvailable(user=self.proposal.registrant,
                                        except_for=['REJECTED'])
        self.assertAllStatusesAvailable(
            user=self.proposal.target_branch.owner)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
