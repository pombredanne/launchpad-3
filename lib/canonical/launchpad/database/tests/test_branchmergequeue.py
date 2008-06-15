# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for BranchMergeQueues."""

__metaclass__ = type


from unittest import TestLoader

from zope.security.proxy import isinstance

from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.database.branchmergequeue import (
    BranchMergeQueueSet, MultiBranchMergeQueue, SingleBranchMergeQueue)
from canonical.launchpad.interfaces.branchmergequeue import (
    IBranchMergeQueue, IBranchMergeQueueSet, IMultiBranchMergeQueue)
from canonical.launchpad.webapp.testing import verifyObject


class TestBranchMergeQueueInterfaces(TestCaseWithFactory):
    """Make sure that the interfaces are verifiable."""

    def test_branch_merge_queue_set(self):
        # A BranchMergeQueueSet implements IBranchMergeQueueSet
        self.assertTrue(verifyObject(
                IBranchMergeQueueSet, BranchMergeQueueSet()))

    def test_single_branch_merge_queue(self):
        # A BranchMergeQueue implements IBranchMergeQueue
        self.assertTrue(verifyObject(
                IBranchMergeQueue,
                SingleBranchMergeQueue(
                    self.factory.makeBranch())))

    def test_multi_branch_merge_queue(self):
        # A MultiBranchMergeQueue implements IMultiBranchMergeQueue
        self.assertTrue(verifyObject(
                IMultiBranchMergeQueue,
                MultiBranchMergeQueue(
                    registrant=self.factory.makePerson(),
                    owner=self.factory.makePerson(),
                    name=self.factory.getUniqueString(),
                    summary=self.factory.getUniqueString())))


class TestBranchMergeQueueSet(TestCaseWithFactory):
    """Test the BranchMergeQueueSet."""

    def test_get_for_branch_with_simple_branch(self):
        # If the branch does not have a merge_queue set then a
        # SingleBranchMergeQueue is returned.
        branch = self.factory.makeBranch()
        queue = BranchMergeQueueSet.getForBranch(branch)
        self.assertTrue(isinstance(queue, SingleBranchMergeQueue))

    def test_get_for_branch_with_merge_queue(self):
        # If the branch does have a merge_queue set, then the associated merge
        # queue is returned.
        new_queue = self.factory.makeBranchMergeQueue()
        branch = self.factory.makeBranch()
        branch.merge_queue = queue
        queue = BranchMergeQueueSet.getForBranch(branch)
        self.assertEqual(new_queue, queue)

    def test_new_branch_merge_queue(self):
        # A new multi-branch merge queue should be created with the
        # appropriate attributes set.
        registrant = self.factory.makePerson()
        owner = self.factory.makePerson()
        queue = BranchMergeQueueSet.newMultiBranchMergeQueue(
            registrant=registrant, owner=owner, name='eric',
            summary='A queue for eric.')
        self.assertTrue(isinstance(queue, MultiBranchMergeQueue))
        self.assertEqual(registrant, queue.registrant)
        self.assertEqual(owner, queue.owner)
        self.assertEqual('eric', queue.name)
        self.assertEqual('A queue for eric.', queue.summary)

    def test_get_by_name_not_existant(self):
        self.assertTrue(BranchMergeQueueSet.getByName('anything') is None)

    def test_get_by_name(self):
        queue = self.factory.makeBranchMergeQueue(name='new-queue')
        get_result = BranchMergeQueueSet.getByName('new-queue')
        self.assertEqual(queue, get_result)


def TestSingleBranchMergeQueue(TestCaseWithFactory):
    """Test the implementation of the interface methods."""

    def test_queue_branches(self):
        # A SingleBranchMergeQueue has one and only one branch, and that is
        # the branch that it is constructed with.
        branch = self.factory.makeBranch()
        queue = SingleBranchMergeQueue(branch)
        branches = queue.branches
        self.assertEqual(1, len(branches))
        self.assertEqual(branch, branches[0])

    def test_queue_items(self):
        # The items of the queue are those merge proposals that are targetted
        # at the branch of the queue, and are in a queued state.
        branch = self.factory.makeBranch()
        queue = SingleBranchMergeQueue(branch)
        first_item = self.factory.makeBranchMergeProposal(
            target_branch=branch, set_state=BranchMergeProposalStatus.QUEUED)
        second_item = self.factory.makeBranchMergeProposal(
            target_branch=branch, set_state=BranchMergeProposalStatus.QUEUED)
        non_queued_item = self.factory.makeBranchMergeProposal(
            target_branch=branch)
        different_queue_item = self.factory.makeBranchMergeProposal()

        items = list(queue.items)
        self.assertEqual(2, len(items))
        self.assertEqual([first_item, second_item], items)


def TestMultiBranchMergeQueue(TestCaseWithFactory):
    """Test the implementation of the interface methods."""

    def _make_branch_and_associate_with_queue(self, queue):
        # Small helper to make a branch and set the merge queue.
        branch = self.factory.makeBranch()
        branch.merge_queue = queue
        return branch

    def test_queue_branches(self):
        # A MultiBranchMergeQueue is able to list the branches that use it.
        queue = self.factory.makeBranchMergeQueue()
        branch1 = self._make_branch_and_associate_with_queue(queue)
        branch2 = self._make_branch_and_associate_with_queue(queue)
        branch3 = self._make_branch_and_associate_with_queue(queue)
        # Result ordering is not guaranteed, so use a set.
        self.assertEqual(set([branch1, branch2, branch3]),
                         set(queue.branches))

    def test_queue_items(self):
        # The items of the queue are those merge proposals that are targetted
        # at any of the branch of the queue, and are in a queued state.
        queue = self.factory.makeBranchMergeQueue()
        branch1 = self._make_branch_and_associate_with_queue(queue)
        branch2 = self._make_branch_and_associate_with_queue(queue)
        first_item = self.factory.makeBranchMergeProposal(
            target_branch=branch1, set_state=BranchMergeProposalStatus.QUEUED)
        second_item = self.factory.makeBranchMergeProposal(
            target_branch=branch2, set_state=BranchMergeProposalStatus.QUEUED)
        non_queued_item = self.factory.makeBranchMergeProposal(
            target_branch=branch1)
        different_queue_item = self.factory.makeBranchMergeProposal()

        items = list(queue.items)
        self.assertEqual(2, len(items))
        self.assertEqual([first_item, second_item], items)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
