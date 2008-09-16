# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Functional tests for branch-related components"""

from unittest import TestLoader, TestCase

from canonical.testing import LaunchpadFunctionalLayer

from canonical.launchpad.components.branch import BranchMergeProposalDelta
from canonical.launchpad.interfaces import BranchMergeProposalStatus
from canonical.launchpad.ftests import login
from canonical.launchpad.testing import LaunchpadObjectFactory


class TestBranchMergeProposalDelta(TestCase):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCase.setUp(self)
        login('foo.bar@canonical.com')
        self.factory = LaunchpadObjectFactory()

    def test_snapshot(self):
        """Test that the snapshot method produces a reasonable snapshot"""
        merge_proposal = self.factory.makeBranchMergeProposal()
        merge_proposal.commit_message = 'foo'
        merge_proposal.whiteboard = 'bar'
        snapshot = BranchMergeProposalDelta.snapshot(merge_proposal)
        self.assertEqual('foo', snapshot.commit_message)
        self.assertEqual('bar', snapshot.whiteboard)

    def test_noModification(self):
        """When there are no modifications, no delta should be returned."""
        merge_proposal = self.factory.makeBranchMergeProposal()
        old_merge_proposal = BranchMergeProposalDelta.snapshot(merge_proposal)
        delta = BranchMergeProposalDelta.construct(
            old_merge_proposal, merge_proposal)
        assert delta is None

    def test_Modification(self):
        """When there are modifications, the delta reflects them."""
        registrant = self.factory.makePerson(
            displayname='Baz Qux', email='baz.qux@example.com',
            password='test')
        merge_proposal = self.factory.makeBranchMergeProposal(
            registrant=registrant)
        old_merge_proposal = BranchMergeProposalDelta.snapshot(merge_proposal)
        merge_proposal.commit_message = 'Change foo into bar.'
        merge_proposal.markAsMerged()
        delta = BranchMergeProposalDelta.construct(
            old_merge_proposal, merge_proposal)
        assert delta is not None
        self.assertEqual('Change foo into bar.', delta.commit_message)
        self.assertEqual(
            {'old': BranchMergeProposalStatus.WORK_IN_PROGRESS,
            'new': BranchMergeProposalStatus.MERGED},
            delta.queue_status)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
