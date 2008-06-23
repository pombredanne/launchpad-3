# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for BranchMergeQueues."""

__metaclass__ = type


from unittest import TestLoader

from zope.security.proxy import isinstance

from canonical.launchpad.ftests import loginPerson
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.database.branch import (
    BranchMergeControlStatus)
from canonical.launchpad.database.branchmergequeue import (
    BranchMergeQueueSet, MultiBranchMergeQueue, SingleBranchMergeQueue)
from canonical.launchpad.interfaces.branchmergequeue import (
    IBranchMergeQueue, IBranchMergeQueueSet, IMultiBranchMergeQueue,
    NotSupportedWithManualQueues)
from canonical.launchpad.interfaces.branchmergeproposal import (
    BranchMergeProposalStatus)
from canonical.launchpad.webapp.testing import verifyObject

from canonical.testing import LaunchpadFunctionalLayer


class TestBranchMergeQueueInterfaces(TestCaseWithFactory):
    """Make sure that the interfaces are verifiable."""

    layer = LaunchpadFunctionalLayer

    def test_branch_merge_queue_set(self):
        # A BranchMergeQueueSet implements IBranchMergeQueueSet
        self.assertTrue(
            verifyObject(IBranchMergeQueueSet, BranchMergeQueueSet()))

    def test_single_branch_merge_queue(self):
        # A SingleBranchMergeQueue implements IBranchMergeQueue
        self.assertTrue(
            verifyObject(
                IBranchMergeQueue,
                SingleBranchMergeQueue(self.factory.makeBranch())))

    def test_multi_branch_merge_queue(self):
        # A MultiBranchMergeQueue implements IMultiBranchMergeQueue
        queue = MultiBranchMergeQueue(
                    registrant=self.factory.makePerson(),
                    owner=self.factory.makePerson(),
                    name=self.factory.getUniqueString(),
                    summary=self.factory.getUniqueString())
        self.assertTrue(verifyObject(IMultiBranchMergeQueue, queue))


class TestBranchMergeQueueSet(TestCaseWithFactory):
    """Test the BranchMergeQueueSet."""

    layer = LaunchpadFunctionalLayer

    def test_get_for_branch_with_no_queue(self):
        # If the branch does not have a merge_queue, and the
        # merge_control_status is set to NO_QUEUE, then None is returned.
        branch = self.factory.makeBranch()
        queue = BranchMergeQueueSet.getForBranch(branch)
        self.assertEqual(BranchMergeControlStatus.NO_QUEUE,
                         branch.merge_control_status)
        self.assertTrue(queue is None)

    def test_get_for_branch_with_manual_queue(self):
        # If the branch does not have a merge_queue set then a
        # SingleBranchMergeQueue is returned.
        branch = self.factory.makeBranch(
            merge_control_status=BranchMergeControlStatus.MANUAL)
        queue = BranchMergeQueueSet.getForBranch(branch)
        self.assertTrue(isinstance(queue, SingleBranchMergeQueue))

    def test_get_for_branch_with_robot_queue(self):
        # If the branch does not have a merge_queue set then a
        # SingleBranchMergeQueue is returned.
        branch = self.factory.makeBranch(
            merge_control_status=BranchMergeControlStatus.ROBOT)
        queue = BranchMergeQueueSet.getForBranch(branch)
        self.assertTrue(isinstance(queue, SingleBranchMergeQueue))

    def test_get_for_branch_with_restricted_robot_queue(self):
        # If the branch does not have a merge_queue set then a
        # SingleBranchMergeQueue is returned.
        branch = self.factory.makeBranch(
            merge_control_status=BranchMergeControlStatus.ROBOT_RESTRICTED)
        queue = BranchMergeQueueSet.getForBranch(branch)
        self.assertTrue(isinstance(queue, SingleBranchMergeQueue))

    def test_get_for_branch_with_merge_queue(self):
        # If the branch does have a merge_queue set, then the associated merge
        # queue is returned.
        new_queue = self.factory.makeBranchMergeQueue()
        branch = self.factory.makeBranch(
            merge_control_status=BranchMergeControlStatus.ROBOT)
        # Login the branch owner to allow launchpad.Edit on the branch.
        loginPerson(branch.owner)
        branch.merge_queue = new_queue
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


class TestSingleBranchMergeQueue(TestCaseWithFactory):
    """Test the implementation of the interface methods."""

    layer = LaunchpadFunctionalLayer

    def test_queue_branches(self):
        # A SingleBranchMergeQueue has one and only one branch, and that is
        # the branch that it is constructed with.
        branch = self.factory.makeBranch(
            merge_control_status=BranchMergeControlStatus.MANUAL)
        queue = SingleBranchMergeQueue(branch)
        self.assertEqual([branch], queue.branches)

    def test_queue_items(self):
        # The items of the queue are those merge proposals that are targetted
        # at the branch of the queue, and are in a queued state.
        branch = self.factory.makeBranch(
            merge_control_status=BranchMergeControlStatus.MANUAL)
        # Login the branch owner to make the proposals.  ANONYMOUS is not
        # good enough as the date_last_modified needs launchpad.AnyPerson.
        loginPerson(branch.owner)
        queue = SingleBranchMergeQueue(branch)
        first_item = self.factory.makeBranchMergeProposal(
            target_branch=branch, set_state=BranchMergeProposalStatus.QUEUED)
        second_item = self.factory.makeBranchMergeProposal(
            target_branch=branch, set_state=BranchMergeProposalStatus.QUEUED)
        non_queued_item = self.factory.makeBranchMergeProposal(
            target_branch=branch)
        different_queue_item = self.factory.makeBranchMergeProposal()

        items = list(queue.items)
        self.assertEqual([first_item, second_item], items)


class BranchMergeQueueTestCase(TestCaseWithFactory):
    """A TestCase that can link branches to queues.

    Also helps by setting the layer.
    """

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        # Login with an administrator as we are not testing authorisation
        # here.
        TestCaseWithFactory.setUp(self, 'foo.bar@canonical.com')

    def _make_branch_and_associate_with_queue(self, queue):
        # Small helper to make a branch and set the merge queue.
        branch = self.factory.makeBranch(
            merge_control_status=BranchMergeControlStatus.ROBOT)
        branch.merge_queue = queue
        return branch


class TestMultiBranchMergeQueue(BranchMergeQueueTestCase):
    """Test the implementation of the interface methods."""

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
        self.assertEqual([first_item, second_item], items)


class TestMergeQueueRestrictedMode(BranchMergeQueueTestCase):
    """A queue is in restricted mode if all of the branches are restricted."""

    def test_single_branch_queue_manual(self):
        # Manual queues are never considered in restricted mode.
        branch = self.factory.makeBranch(
            merge_control_status=BranchMergeControlStatus.MANUAL)
        queue = BranchMergeQueueSet.getForBranch(branch)
        self.assertEqual(False, queue.restricted_mode)
        # You cannot set restricted_mode for Manual queues.
        self.assertRaises(
            NotSupportedWithManualQueues,
            setattr, queue, 'restricted_mode', True)

    def test_single_branch_queue_robot(self):
        # Robot queues are either restricted or not.
        branch = self.factory.makeBranch(
            merge_control_status=BranchMergeControlStatus.ROBOT)
        queue = BranchMergeQueueSet.getForBranch(branch)
        self.assertEqual(False, queue.restricted_mode)
        # The merge_control_status can be set by either the target branch, or
        # throught the queue itself.
        branch.merge_control_status = (
            BranchMergeControlStatus.ROBOT_RESTRICTED)
        self.assertEqual(True, queue.restricted_mode)
        # Setting the restricted mode through the queue updates the
        # merge_control_status of the branch.
        queue.restricted_mode = False
        self.assertEqual(False, queue.restricted_mode)
        self.assertEqual(
            BranchMergeControlStatus.ROBOT, branch.merge_control_status)
        queue.restricted_mode = True
        self.assertEqual(True, queue.restricted_mode)
        self.assertEqual(
            BranchMergeControlStatus.ROBOT_RESTRICTED,
            branch.merge_control_status)

    def test_multi_branch_queue_no_branches(self):
        # A multi branch queue with no branches is not considered restricted.
        queue = self.factory.makeBranchMergeQueue()
        self.assertEqual(False, queue.restricted_mode)
        # Attempting to set the restricted_mode on a merge queue with no
        # branches does not really make sense, but is valid to do, but does
        # nothing.
        queue.restricted_mode = True
        self.assertEqual(False, queue.restricted_mode)

    def test_multi_branch_queue_with_branches(self):
        # For a multi branch queue to be in restricted mode, all of the
        # associated branches must be in restricted mode.
        queue = self.factory.makeBranchMergeQueue()
        branch1 = self._make_branch_and_associate_with_queue(queue)
        branch2 = self._make_branch_and_associate_with_queue(queue)
        self.assertEqual(False, queue.restricted_mode)
        # Setting one branch to restricted, still leaves the queue
        # unrestricted.
        branch1.merge_control_status = (
            BranchMergeControlStatus.ROBOT_RESTRICTED)
        self.assertEqual(False, queue.restricted_mode)
        # Setting the second branch to restricted changes the restricted state
        # of the queue.
        branch2.merge_control_status = (
            BranchMergeControlStatus.ROBOT_RESTRICTED)
        self.assertEqual(True, queue.restricted_mode)

        # Setting the restricted_mode on the queue updates the status for all
        # branches, overriding whatever status they may be in.
        queue.restricted_mode = False
        self.assertEqual(False, queue.restricted_mode)
        self.assertEqual(
            BranchMergeControlStatus.ROBOT, branch1.merge_control_status)
        self.assertEqual(
            BranchMergeControlStatus.ROBOT, branch2.merge_control_status)

        queue.restricted_mode = True
        self.assertEqual(True, queue.restricted_mode)
        self.assertEqual(
            BranchMergeControlStatus.ROBOT_RESTRICTED,
            branch1.merge_control_status)
        self.assertEqual(
            BranchMergeControlStatus.ROBOT_RESTRICTED,
            branch2.merge_control_status)


class TestMergeQueueFront(BranchMergeQueueTestCase):
    """Test the front item respects the restricted flag.

    If the queue is in restricted mode, the front proposal must be in
    QUEUED_RESTRICTED state.
    """

    def test_empty_single_queue_returns_none(self):
        # An empty queue returns None for front.
        branch = self.factory.makeBranch(
            merge_control_status=BranchMergeControlStatus.ROBOT)
        queue = BranchMergeQueueSet.getForBranch(branch)
        self.assertTrue(queue.front is None)

    def test_empty_multi_queue_returns_none(self):
        # An empty queue returns None for front.
        queue = self.factory.makeBranchMergeQueue()
        branch1 = self._make_branch_and_associate_with_queue(queue)
        branch2 = self._make_branch_and_associate_with_queue(queue)
        self.assertTrue(queue.front is None)

    def test_single_front_unrestricted(self):
        # When in unrestricted mode, front will be the head of the queue.
        branch = self.factory.makeBranch(
            merge_control_status=BranchMergeControlStatus.ROBOT)
        queue = BranchMergeQueueSet.getForBranch(branch)
        first_item = self.factory.makeBranchMergeProposal(
            target_branch=branch, set_state=BranchMergeProposalStatus.QUEUED)
        second_item = self.factory.makeBranchMergeProposal(
            target_branch=branch, set_state=BranchMergeProposalStatus.QUEUED)
        self.assertEqual(first_item, queue.front)

    def test_single_front_restricted(self):
        # When in restricted mode, front will be the first QUEUED_RESTRICTED
        # proposal.
        branch = self.factory.makeBranch(
            merge_control_status=BranchMergeControlStatus.ROBOT)
        queue = BranchMergeQueueSet.getForBranch(branch)
        first_item = self.factory.makeBranchMergeProposal(
            target_branch=branch, set_state=BranchMergeProposalStatus.QUEUED)
        second_item = self.factory.makeBranchMergeProposal(
            target_branch=branch, set_state=BranchMergeProposalStatus.QUEUED)
        queue.restricted_mode = True
        self.assertTrue(queue.front is None)
        # If the second item is maked as QUEUED_RESTRICTED, it wil be move to
        # the front.
        queue.allowRestrictedLanding(second_item)
        self.assertEqual(second_item, queue.front)

    def test_multi_front_no_restrictions(self):
        # If none of the queue branches is in restricted mode, the queue
        # operates as expected, with the head of the queue being the front.
        queue = self.factory.makeBranchMergeQueue()
        branch1 = self._make_branch_and_associate_with_queue(queue)
        branch2 = self._make_branch_and_associate_with_queue(queue)
        self.assertEqual(False, queue.restricted_mode)
        first_item = self.factory.makeBranchMergeProposal(
            target_branch=branch1, set_state=BranchMergeProposalStatus.QUEUED)
        second_item = self.factory.makeBranchMergeProposal(
            target_branch=branch2, set_state=BranchMergeProposalStatus.QUEUED)
        self.assertEqual(first_item, queue.front)

    def test_multi_front_one_restrictions(self):
        # If one of the branches is in restricted mode, then the QUEUED items
        # for that branch will not be selected as `front`.
        queue = self.factory.makeBranchMergeQueue()
        branch1 = self._make_branch_and_associate_with_queue(queue)
        branch2 = self._make_branch_and_associate_with_queue(queue)
        self.assertEqual(False, queue.restricted_mode)
        first_item = self.factory.makeBranchMergeProposal(
            target_branch=branch1, set_state=BranchMergeProposalStatus.QUEUED)
        second_item = self.factory.makeBranchMergeProposal(
            target_branch=branch2, set_state=BranchMergeProposalStatus.QUEUED)
        branch1.merge_control_status = (
            BranchMergeControlStatus.ROBOT_RESTRICTED)
        self.assertEqual(second_item, queue.front)
        # If the first_item however is QUEUED_RESTRICTED, it is chosen as the
        # front of the queue.
        queue.allowRestrictedLanding(first_item)
        self.assertEqual(first_item, queue.front)

    def test_multi_front_queue_restricted(self):
        # If the queue is in restricted mode, then only QUEUED_RESTRICTED
        # proposals will be considered for front.
        queue = self.factory.makeBranchMergeQueue()
        branch1 = self._make_branch_and_associate_with_queue(queue)
        branch2 = self._make_branch_and_associate_with_queue(queue)
        self.assertEqual(False, queue.restricted_mode)
        first_item = self.factory.makeBranchMergeProposal(
            target_branch=branch1, set_state=BranchMergeProposalStatus.QUEUED)
        second_item = self.factory.makeBranchMergeProposal(
            target_branch=branch2, set_state=BranchMergeProposalStatus.QUEUED)
        queue.restricted_mode = True
        self.assertTrue(queue.front is None)
        # If the second_item however is QUEUED_RESTRICTED, it is chosen over
        # the first_item that is just QUEUED.
        queue.allowRestrictedLanding(second_item)
        self.assertEqual(second_item, queue.front)
        # If the first_item however is QUEUED_RESTRICTED, it is chosen as the
        # front of the queue.
        queue.allowRestrictedLanding(first_item)
        self.assertEqual(first_item, queue.front)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
