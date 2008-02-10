# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for BranchMergeProposals."""

__metaclass__ = type

from unittest import TestCase, TestLoader

from canonical.launchpad.ftests import ANONYMOUS, login, logout
from canonical.launchpad.interfaces import (
    BadStateTransition, BranchMergeProposalStatus)
from canonical.launchpad.testing import LaunchpadObjectFactory

from canonical.testing import LaunchpadFunctionalLayer


class TestBranchMergeProposalTransitions(TestCase):
    """Test the state transitions of branch merge proposals."""

    layer = LaunchpadFunctionalLayer

    # All transitions between states are handled my method calls
    # on the proposal.
    transition_functions = {
        BranchMergeProposalStatus.WORK_IN_PROGRESS: 'setAsWorkInProgress',
        BranchMergeProposalStatus.NEEDS_REVIEW: 'requestReview',
        BranchMergeProposalStatus.CODE_APPROVED: 'approveBranch',
        BranchMergeProposalStatus.REJECTED: 'rejectBranch',
        BranchMergeProposalStatus.MERGED: 'markAsMerged',
        BranchMergeProposalStatus.MERGE_FAILED: 'mergeFailed',
        BranchMergeProposalStatus.QUEUED: 'enqueue',
        BranchMergeProposalStatus.SUPERSEDED: 'resubmit',
        }

    def setUp(self):
        TestCase.setUp(self)
        login(ANONYMOUS)
        self.factory = LaunchpadObjectFactory()
        self.target_branch = self.factory.makeBranch()
        login(self.target_branch.owner.preferredemail.email)

    def assertProposalState(self, proposal, state):
        """Assert that the `queue_status` of the `proposal` is `state`."""
        self.assertEqual(state, proposal.queue_status,
                         "Wrong state, expected %s, got %s"
                         % (state.title, proposal.queue_status.title))

    def _attemptTransition(self, proposal, to_state):
        """Try to transition the proposal into the state `to_state`."""
        method = getattr(proposal, self.transition_functions[to_state])
        if to_state in (BranchMergeProposalStatus.CODE_APPROVED,
                        BranchMergeProposalStatus.REJECTED,
                        BranchMergeProposalStatus.QUEUED):
            args = [proposal.target_branch.owner, 'some_revision_id']
        elif to_state in (BranchMergeProposalStatus.MERGE_FAILED,
                          BranchMergeProposalStatus.SUPERSEDED):
            args = [proposal.registrant]
        else:
            args = []
        method(*args)

    def assertGoodTransition(self, from_state, to_state):
        """Assert that we can go from `from_state` to `to_state`."""
        proposal = self.factory.makeBranchMergeProposal(
            target_branch=self.target_branch,
            set_state=from_state)
        self.assertProposalState(proposal, from_state)
        self._attemptTransition(proposal, to_state)
        self.assertProposalState(proposal, to_state)

    def assertBadTransition(self, from_state, to_state):
        """Assert that trying to go from `from_state` to `to_state` fails."""
        proposal = self.factory.makeBranchMergeProposal(
            target_branch=self.target_branch,
            set_state=from_state)
        self.assertProposalState(proposal, from_state)
        self.assertRaises(BadStateTransition,
                          self._attemptTransition,
                          proposal, to_state)

    def assertAllTransitionsGood(self, from_state):
        """Assert that we can go from `from_state` to any state."""
        for status in BranchMergeProposalStatus.items:
            self.assertGoodTransition(from_state, status)

    def assertTerminatingState(self, from_state):
        """Assert that the proposal cannot go to any other state."""
        for status in BranchMergeProposalStatus.items:
            self.assertBadTransition(from_state, status)

    def test_transitions_from_wip(self):
        """We can go from work in progress to any other state."""
        self.assertAllTransitionsGood(
            BranchMergeProposalStatus.WORK_IN_PROGRESS)

    def test_transitions_from_needs_review(self):
        """We can go from needs review to any other state."""
        self.assertAllTransitionsGood(
            BranchMergeProposalStatus.NEEDS_REVIEW)

    def test_transitions_from_code_approved(self):
        """We can go from code_approved to any other state."""
        self.assertAllTransitionsGood(
            BranchMergeProposalStatus.CODE_APPROVED)

    def test_transitions_from_rejected(self):
        """Rejected proposals can only be resubmitted."""
        # Test the transitions from rejected.
        [wip, needs_review, code_approved, rejected,
         merged, merge_failed, queued, superseded
         ] = BranchMergeProposalStatus.items
         merged, merge_failed, superseded] = BranchMergeProposalStatus.items

        for status in (wip, needs_review, code_approved, rejected,
                       merged, queued, merge_failed):
            # All bad, rejected is a final state.
            self.assertBadTransition(rejected, status)
        # Can resubmit (supersede) a rejected proposal.
        self.assertGoodTransition(rejected, superseded)

    def test_transitions_from_merged(self):
        """Merged is a terminal state, so no transitions are valid."""
        self.assertTerminatingState(BranchMergeProposalStatus.MERGED)

    def test_transitions_from_merge_failed(self):
        """We can go from merge failed to any other state."""
        self.assertAllTransitionsGood(BranchMergeProposalStatus.MERGE_FAILED)

    def test_transitions_from_queued(self):
        """Queued proposals can only be marked as merged or merge failed.
        Queued proposals can be moved out of the queue using the `dequeue`
        method, and no other transitions are valid.
        """
        queued = BranchMergeProposalStatus.QUEUED
        for status in BranchMergeProposalStatus.items:
            if status in (BranchMergeProposalStatus.MERGED,
                          BranchMergeProposalStatus.MERGE_FAILED):
                self.assertGoodTransition(queued, status)
            else:
                self.assertBadTransition(queued, status)

        proposal = self.factory.makeBranchMergeProposal(
            target_branch=self.target_branch, set_state=queued)
        proposal.dequeue()
        self.assertProposalState(
            proposal, BranchMergeProposalStatus.CODE_APPROVED)

    def test_transitions_from_superseded(self):
        """Superseded is a terminal state, so no transitions are valid."""
        self.assertTerminatingState(BranchMergeProposalStatus.SUPERSEDED)


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


class TestBranchMergeProposalQueuing(TestCase):
    """Test the enqueuing and dequeuing of merge proposals."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCase.setUp(self)
        login(ANONYMOUS)
        factory = LaunchpadObjectFactory()
        self.target_branch = factory.makeBranch()
        login(self.target_branch.owner.preferredemail.email)
        self.proposals = [
            factory.makeBranchMergeProposal(self.target_branch)
            for x in range(4)]

    def test_empty_target_queue(self):
        """If there are no proposals targetted to the branch, the queue has
        nothing in it."""
        queued_proposals = list(self.target_branch.getMergeQueue())
        self.assertEqual(0, len(queued_proposals),
                         "The initial merge queue should be empty.")

    def test_single_item_in_queue(self):
        """Enqueing a proposal makes it visible in the target branch queue."""
        proposal = self.proposals[0]
        proposal.enqueue(self.target_branch.owner, 'some-revision-id')
        queued_proposals = list(self.target_branch.getMergeQueue())
        self.assertEqual(1, len(queued_proposals),
                         "Should have one entry in the queue, got %s"
                         % len(queued_proposals))

    def test_queue_ordering(self):
        """Assert that the queue positions are based on the order the
        proposals were enqueued."""
        enqueued_order = []
        for proposal in self.proposals[:-1]:
            enqueued_order.append(proposal.source_branch.unique_name)
            proposal.enqueue(self.target_branch.owner, 'some-revision')
        queued_proposals = list(self.target_branch.getMergeQueue())
        queue_order = [proposal.source_branch.unique_name
                       for proposal in queued_proposals]
        self.assertEqual(
            enqueued_order, queue_order,
            "The queue should be in the order they were added. "
            "Expected %s, got %s" % (enqueued_order, queue_order))

        # Move the last one to the front.
        proposal = queued_proposals[-1]
        proposal.moveToFrontOfQueue()

        new_queue_order = enqueued_order[-1:] + enqueued_order[:-1]

        queued_proposals = list(self.target_branch.getMergeQueue())
        queue_order = [proposal.source_branch.unique_name
                       for proposal in queued_proposals]
        self.assertEqual(
            new_queue_order, queue_order,
            "The last should now be at the front. "
            "Expected %s, got %s" % (new_queue_order, queue_order))

        # Remove the proposal from the middle of the queue.
        proposal = queued_proposals[1]
        proposal.dequeue()

        del new_queue_order[1]

        queued_proposals = list(self.target_branch.getMergeQueue())
        queue_order = [proposal.source_branch.unique_name
                       for proposal in queued_proposals]
        self.assertEqual(
            new_queue_order, queue_order,
            "There should be only two queued items now. "
            "Expected %s, got %s" % (new_queue_order, queue_order))


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
