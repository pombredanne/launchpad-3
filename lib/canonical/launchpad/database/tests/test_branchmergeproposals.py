# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for BranchMergeProposals."""

__metaclass__ = type

from unittest import TestCase, TestLoader

from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import ANONYMOUS, login, logout, syncUpdate
from canonical.launchpad.database.branchmergeproposal import (
    BranchMergeProposal)
from canonical.launchpad.interfaces import (
    BadStateTransition, BranchMergeProposalStatus)
from canonical.launchpad.testing import LaunchpadObjectFactory

from canonical.testing import LaunchpadFunctionalLayer


class TestBranchMergeProposalTransitions(TestCase):
    """Test the state transitions of branch merge proposals."""

    layer = LaunchpadFunctionalLayer

    transition_function = {
        BranchMergeProposalStatus.WORK_IN_PROGRESS:
            BranchMergeProposal.setAsWorkInProgress,
        BranchMergeProposalStatus.NEEDS_REVIEW:
            BranchMergeProposal.requestReview,
        BranchMergeProposalStatus.CODE_APPROVED:
            BranchMergeProposal.approveBranch,
        BranchMergeProposalStatus.REJECTED:
            BranchMergeProposal.rejectBranch,
        BranchMergeProposalStatus.MERGED:
            BranchMergeProposal.markAsMerged,
        BranchMergeProposalStatus.MERGE_FAILED:
            BranchMergeProposal.mergeFailed,
        BranchMergeProposalStatus.SUPERCEDED:
            BranchMergeProposal.resubmit,
        }

    def setUp(self):
        TestCase.setUp(self)
        login('test@canonical.com')

        self.factory = LaunchpadObjectFactory()

    def assertProposalState(self, proposal, state):
        self.assertEqual(state, proposal.queue_status,
                         "Wrong state, expected %s, got %s"
                         % (state.title, proposal.queue_status.title))

    def _transitionArgs(self, to_state, proposal):
        # Return the appropriate args for a call to the transition state.
        # The security proxy seems to not work with unbound methods,
        # so remove the proxy to pass in the proposal as 'self'.
        naked_proposal = removeSecurityProxy(proposal)
        if to_state in (BranchMergeProposalStatus.CODE_APPROVED,
                        BranchMergeProposalStatus.REJECTED):
            return [naked_proposal, proposal.target_branch.owner,
                    'some_revision_id']
        elif to_state in (BranchMergeProposalStatus.MERGE_FAILED,
                          BranchMergeProposalStatus.SUPERCEDED):
            return [naked_proposal, proposal.registrant]
        else:
            return [naked_proposal]

    def assertGoodTransition(self, from_state, to_state, factory):
        # Check that the state transition fails.
        proposal = factory()
        self.assertProposalState(proposal, from_state)
        args = self._transitionArgs(to_state, proposal)
        self.transition_function[to_state](*args)
        self.assertProposalState(proposal, to_state)

    def assertBadTransition(self, from_state, to_state, factory):
        # Check that the state transition fails.
        proposal = factory()
        self.assertProposalState(proposal, from_state)
        args = self._transitionArgs(to_state, proposal)
        self.assertRaises(BadStateTransition,
                          self.transition_function[to_state],
                          *args)

    def test_transitions_from_wip(self):
        # Test the transitions from work in progress.
        [wip, needs_review, code_approved, rejected,
         merged, merge_failed, superceded] = BranchMergeProposalStatus.items

        def make_wip_proposal():
            return self.factory.makeProposalToMerge()

        self.assertBadTransition(wip, wip, make_wip_proposal)

        for status in (needs_review, code_approved, rejected,
                       merged, merge_failed, superceded):
            self.assertGoodTransition(wip, status, make_wip_proposal)

    def test_transitions_from_needs_review(self):
        # Test the transitions from work in progress.
        [wip, needs_review, code_approved, rejected,
         merged, merge_failed, superceded] = BranchMergeProposalStatus.items

        def make_needs_review_proposal():
            proposal = self.factory.makeProposalToMerge()
            proposal.requestReview()
            return proposal

        for status in (wip, code_approved, rejected,
                       merged, merge_failed, superceded):
            # All good.
            self.assertGoodTransition(
                needs_review, status, make_needs_review_proposal)

        self.assertBadTransition(
            needs_review, needs_review, make_needs_review_proposal)

    def test_transitions_from_code_approved(self):
        # Test the transitions from work in progress.
        [wip, needs_review, code_approved, rejected,
         merged, merge_failed, superceded] = BranchMergeProposalStatus.items

        def make_approved_proposal():
            proposal = self.factory.makeProposalToMerge()
            proposal.approveBranch(
                proposal.target_branch.owner, 'some_revision')
            return proposal

        for status in (wip, needs_review, rejected,
                       merged, merge_failed, superceded):
            # All good.
            self.assertGoodTransition(
                code_approved, status, make_approved_proposal)

        self.assertBadTransition(
            code_approved, code_approved, make_approved_proposal)

    def test_transitions_from_rejected(self):
        # Test the transitions from work in progress.
        [wip, needs_review, code_approved, rejected,
         merged, merge_failed, superceded] = BranchMergeProposalStatus.items

        def make_rejected_proposal():
            proposal = self.factory.makeProposalToMerge()
            proposal.rejectBranch(
                proposal.target_branch.owner, 'some_revision')
            return proposal

        for status in (wip, needs_review, code_approved, rejected,
                       merged, merge_failed):
            # All bad, rejected is a final state.
            self.assertBadTransition(
                rejected, status, make_rejected_proposal)
        # Can resubmit (supercede) a rejected proposal.
        self.assertGoodTransition(
            rejected, superceded, make_rejected_proposal)

    def test_transitions_from_merged(self):
        # Test the transitions from work in progress.
        [wip, needs_review, code_approved, rejected,
         merged, merge_failed, superceded] = BranchMergeProposalStatus.items

        def make_merged_proposal():
            proposal = self.factory.makeProposalToMerge()
            proposal.markAsMerged()
            return proposal

        for status in BranchMergeProposalStatus.items:
            # All bad, merged is a final state.
            self.assertBadTransition(
                merged, status, make_merged_proposal)

    def test_transitions_from_merge_failed(self):
        # Test the transitions from work in progress.
        [wip, needs_review, code_approved, rejected,
         merged, merge_failed, superceded] = BranchMergeProposalStatus.items

        def make_merge_failed_proposal():
            proposal = self.factory.makeProposalToMerge()
            proposal.mergeFailed(proposal.target_branch.owner)
            return proposal

        for status in (wip, needs_review, code_approved, rejected,
                       merged, superceded):
            # All good.
            self.assertGoodTransition(
                merge_failed, status, make_merge_failed_proposal)

        self.assertBadTransition(
            merge_failed, merge_failed, make_merge_failed_proposal)

    def test_transitions_from_superceded(self):
        # Test the transitions from work in progress.
        [wip, needs_review, code_approved, rejected,
         merged, merge_failed, superceded] = BranchMergeProposalStatus.items

        def make_superceded_proposal():
            proposal = self.factory.makeProposalToMerge()
            proposal.resubmit(proposal.registrant)
            return proposal

        for status in BranchMergeProposalStatus.items:
            # All bad.
            self.assertBadTransition(
                superceded, status, make_superceded_proposal)



class TestBranchMergeProposalCanReview(TestCase):
    """Test the different cases that makes a branch deletable or not."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login('test@canonical.com')

        factory = LaunchpadObjectFactory()
        self.source_branch = factory.makeBranch()
        self.target_branch = factory.makeBranch(
            product=self.source_branch.product)
        registrant = factory.makePerson()
        self.proposal = self.source_branch.addLandingTarget(
            registrant, self.target_branch)

    def tearDown(self):
        logout()

    def test_validReviewer(self):
        """A newly created branch can be deleted without any problems."""
        self.assertEqual(self.proposal.isPersonValidReviewer(None),
                         False, "No user cannot review code")
        # The owner of the target branch is a valid reviewer.
        self.assertEqual(
            self.proposal.isPersonValidReviewer(
                self.target_branch.owner),
            True, "No user cannot review code")


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
