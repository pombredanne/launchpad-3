# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for BranchMergeProposals."""

__metaclass__ = type

from unittest import TestCase, TestLoader

from zope.component import getUtility

from canonical.launchpad.database.branchmergeproposal import (
    BranchMergeProposalGetter)
from canonical.launchpad.interfaces import WrongBranchMergeProposal
from canonical.launchpad.event import SQLObjectCreatedEvent
from canonical.launchpad.ftests import ANONYMOUS, login, logout, syncUpdate
from canonical.launchpad.interfaces import (
    BadStateTransition, BranchMergeProposalStatus,
    BranchSubscriptionNotificationLevel, CodeReviewNotificationLevel,
    IBranchMergeProposalGetter)
from canonical.launchpad.interfaces.person import IPersonSet
from canonical.launchpad.interfaces.product import IProductSet
from canonical.launchpad.interfaces.codereviewcomment import CodeReviewVote
from canonical.launchpad.testing import (
    LaunchpadObjectFactory, TestCaseWithFactory, time_counter)

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
        owner = self.factory.makePerson()
        self.target_branch = self.factory.makeBranch(owner=owner)
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

    def test_valid_transition_graph_is_complete(self):
        """The valid transition graph should have a key for all possible
        queue states."""
        from canonical.launchpad.database.branchmergeproposal import (
            VALID_TRANSITION_GRAPH)
        keys = VALID_TRANSITION_GRAPH.keys()
        all_states = BranchMergeProposalStatus.items
        self.assertEqual(sorted(all_states), sorted(keys),
                         "Missing possible states from the transition graph.")

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


class TestBranchMergeProposalQueueing(TestCase):
    """Test the enqueueing and dequeueing of merge proposals."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCase.setUp(self)
        login(ANONYMOUS)
        factory = LaunchpadObjectFactory()
        owner = factory.makePerson()
        self.target_branch = factory.makeBranch(owner=owner)
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
                         "Should have one entry in the queue, got %s."
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
        syncUpdate(proposal)

        del new_queue_order[1]

        queued_proposals = list(self.target_branch.getMergeQueue())
        queue_order = [proposal.source_branch.unique_name
                       for proposal in queued_proposals]
        self.assertEqual(
            new_queue_order, queue_order,
            "There should be only two queued items now. "
            "Expected %s, got %s" % (new_queue_order, queue_order))


class TestRootComment(TestCase):
    """Test the behavior of the root_comment attribute"""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCase.setUp(self)
        login('foo.bar@canonical.com')
        self.factory = LaunchpadObjectFactory()
        self.merge_proposal = self.factory.makeBranchMergeProposal()

    def test_orderedByDateNotInsertion(self):
        """Root is determined by create date, not insert order"""
        counter = time_counter()
        oldest_date, middle_date, newest_date = [counter.next() for index in
            (1, 2, 3)]
        comment1 = self.merge_proposal.createComment(
            self.merge_proposal.registrant, "Subject",
            _date_created=middle_date)
        self.assertEqual(comment1, self.merge_proposal.root_comment)
        comment2 = self.merge_proposal.createComment(
            self.merge_proposal.registrant, "Subject",
            _date_created=newest_date)
        self.assertEqual(comment1, self.merge_proposal.root_comment)
        comment3 = self.merge_proposal.createComment(
            self.merge_proposal.registrant, "Subject",
            _date_created=oldest_date)
        self.assertEqual(comment3, self.merge_proposal.root_comment)


class TestMergeProposalAllComments(TestCase):
    """Tester for `BranchMergeProposal.all_comments`."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCase.setUp(self)
        # Testing behavior, not permissions here.
        login('foo.bar@canonical.com')
        self.factory = LaunchpadObjectFactory()
        self.merge_proposal = self.factory.makeBranchMergeProposal()

    def test_all_comments(self):
        """Ensure all comments associated with the proposal are returned."""
        comment1 = self.merge_proposal.createComment(
            self.merge_proposal.registrant, "Subject")
        comment2 = self.merge_proposal.createComment(
            self.merge_proposal.registrant, "Subject")
        comment3 = self.merge_proposal.createComment(
            self.merge_proposal.registrant, "Subject")
        self.assertEqual(
            set([comment1, comment2, comment3]),
            set(self.merge_proposal.all_comments))


class TestMergeProposalGetComment(TestCase):
    """Tester for `BranchMergeProposal.getComment`."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCase.setUp(self)
        # Testing behavior, not permissions here.
        login('foo.bar@canonical.com')
        self.factory = LaunchpadObjectFactory()
        self.merge_proposal = self.factory.makeBranchMergeProposal()
        self.merge_proposal2 = self.factory.makeBranchMergeProposal()
        self.comment = self.merge_proposal.createComment(
            self.merge_proposal.registrant, "Subject")

    def test_getComment(self):
        """Tests that we can get a comment."""
        self.assertEqual(
            self.comment, self.merge_proposal.getComment(self.comment.id))

    def test_getCommentWrongBranchMergeProposal(self):
        """Tests that we can get a comment."""
        self.assertRaises(WrongBranchMergeProposal,
                          self.merge_proposal2.getComment, self.comment.id)


class TestMergeProposalNotification(TestCaseWithFactory):
    """Test that events are created when merge proposals are manipulated"""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self, user='test@canonical.com')

    def test_notifyOnCreate(self):
        """Ensure that a notification is emitted on creation"""
        source_branch = self.factory.makeBranch()
        target_branch = self.factory.makeBranch(product=source_branch.product)
        registrant = self.factory.makePerson()
        result, event = self.assertNotifies(SQLObjectCreatedEvent,
            source_branch.addLandingTarget, registrant, target_branch)
        self.assertEqual(result, event.object)

    def test_getNotificationRecipients(self):
        """Ensure that recipients can be added/removed with subscribe"""
        bmp = self.factory.makeBranchMergeProposal()
        # Both of the branch owners are now subscribed to their own
        # branches with full code review notification level set.
        source_owner = bmp.source_branch.owner
        target_owner = bmp.target_branch.owner
        recipients = bmp.getNotificationRecipients(
            CodeReviewNotificationLevel.STATUS)
        subscriber_set = set([source_owner, target_owner])
        self.assertEqual(subscriber_set, set(recipients.keys()))
        source_subscriber = self.factory.makePerson()
        bmp.source_branch.subscribe(source_subscriber,
            BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.FULL)
        recipients = bmp.getNotificationRecipients(
            CodeReviewNotificationLevel.STATUS)
        subscriber_set.add(source_subscriber)
        self.assertEqual(subscriber_set, set(recipients.keys()))
        bmp.source_branch.subscribe(source_subscriber,
            BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.NOEMAIL)
        # By specifying no email, they will no longer get email.
        subscriber_set.remove(source_subscriber)
        recipients = bmp.getNotificationRecipients(
            CodeReviewNotificationLevel.STATUS)
        self.assertEqual(subscriber_set, set(recipients.keys()))

    def test_getNotificationRecipientLevels(self):
        """Ensure that only recipients with the right level are returned"""
        bmp = self.factory.makeBranchMergeProposal()
        full_subscriber = self.factory.makePerson()
        bmp.source_branch.subscribe(full_subscriber,
            BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.FULL)
        status_subscriber = self.factory.makePerson()
        bmp.source_branch.subscribe(status_subscriber,
            BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.STATUS)
        recipients = bmp.getNotificationRecipients(
            CodeReviewNotificationLevel.STATUS)
        # Both of the branch owners are now subscribed to their own
        # branches with full code review notification level set.
        source_owner = bmp.source_branch.owner
        target_owner = bmp.target_branch.owner
        self.assertEqual(set([full_subscriber, status_subscriber,
                              source_owner, target_owner]),
                         set(recipients.keys()))
        recipients = bmp.getNotificationRecipients(
            CodeReviewNotificationLevel.FULL)
        self.assertEqual(set([full_subscriber, source_owner, target_owner]),
                         set(recipients.keys()))

    def test_getNotificationRecipientsAnyBranch(self):
        dependent_branch = self.factory.makeBranch()
        bmp = self.factory.makeBranchMergeProposal(
            dependent_branch=dependent_branch)
        recipients = bmp.getNotificationRecipients(
            CodeReviewNotificationLevel.NOEMAIL)
        source_owner = bmp.source_branch.owner
        target_owner = bmp.target_branch.owner
        dependent_owner = bmp.dependent_branch.owner
        self.assertEqual(set([source_owner, target_owner, dependent_owner]),
                         set(recipients.keys()))
        source_subscriber = self.factory.makePerson()
        bmp.source_branch.subscribe(source_subscriber,
            BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.FULL)
        target_subscriber = self.factory.makePerson()
        bmp.target_branch.subscribe(target_subscriber,
            BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.FULL)
        dependent_subscriber = self.factory.makePerson()
        bmp.dependent_branch.subscribe(dependent_subscriber,
            BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.FULL)
        recipients = bmp.getNotificationRecipients(
            CodeReviewNotificationLevel.FULL)
        self.assertEqual(
            set([source_subscriber, target_subscriber, dependent_subscriber,
                 source_owner, target_owner, dependent_owner]),
            set(recipients.keys()))


class TestGetAddress(TestCaseWithFactory):
    """Test that the address property gives expected results."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self, user='test@canonical.com')

    def test_address(self):
        merge_proposal = self.factory.makeBranchMergeProposal()
        expected = 'mp+%d@code.launchpad.dev' % merge_proposal.id
        self.assertEqual(expected, merge_proposal.address)


class TestBranchMergeProposalGetter(TestCaseWithFactory):
    """Test that the BranchMergeProposalGetter behaves as expected."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self, user='test@canonical.com')

    def test_get(self):
        """Ensure the correct merge proposal is returned."""
        merge_proposal = self.factory.makeBranchMergeProposal()
        self.assertEqual(merge_proposal,
            BranchMergeProposalGetter().get(merge_proposal.id))

    def test_get_as_utility(self):
        """Ensure the correct merge proposal is returned."""
        merge_proposal = self.factory.makeBranchMergeProposal()
        utility = getUtility(IBranchMergeProposalGetter)
        retrieved = utility.get(merge_proposal.id)
        self.assertEqual(merge_proposal, retrieved)


class TestBranchMergeProposalGetterGetProposals(TestCaseWithFactory):
    """Test the getProposalsForContext method."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        # Use an administrator so the permission checks for things
        # like adding landing targets and setting privacy on the branches
        # are allowed.
        TestCaseWithFactory.setUp(self, user='foo.bar@canonical.com')

    def _make_merge_proposal(self, owner_name, product_name, branch_name,
                             needs_review=False, registrant=None):
        # A helper method to make the tests readable.
        owner = getUtility(IPersonSet).getByName(owner_name)
        if owner is None:
            owner = self.factory.makePerson(name=owner_name)
        product = getUtility(IProductSet).getByName(product_name)
        if product is None:
            product = self.factory.makeProduct(name=product_name)
        branch = self.factory.makeBranch(
            product=product, owner=owner, registrant=registrant,
            name=branch_name)
        if registrant is None:
            registrant = owner
        bmp = branch.addLandingTarget(
            registrant=registrant,
            target_branch=self.factory.makeBranch(product=product))
        if needs_review:
            bmp.requestReview()
            syncUpdate(bmp)
        return bmp

    def _get_merge_proposals(self, context, status=None,
                             visible_by_user=None):
        # Helper method to return tuples of source branch details.
        results = BranchMergeProposalGetter.getProposalsForContext(
            context, status, visible_by_user)
        return sorted([bmp.source_branch.unique_name for bmp in results])

    def test_created_proposal_default_status(self):
        # When we create a merge proposal using the helper method, the default
        # status of the proposal is work in progress.
        in_progress = self._make_merge_proposal('albert', 'november', 'work')
        self.assertEqual(
            BranchMergeProposalStatus.WORK_IN_PROGRESS,
            in_progress.queue_status)

    def test_created_proposal_review_status(self):
        # If needs_review is set to True, the created merge proposal is set in
        # the needs review state.
        needs_review = self._make_merge_proposal(
            'bob', 'november', 'work', needs_review=True)
        self.assertEqual(
            BranchMergeProposalStatus.NEEDS_REVIEW,
            needs_review.queue_status)

    def test_all_for_product_restrictions(self):
        # Queries on product should limit results to that product.
        self._make_merge_proposal('albert', 'november', 'work')
        self._make_merge_proposal('bob', 'november', 'work')
        # And make a proposal for another product to make sure that it doesn't
        # appear
        self._make_merge_proposal('charles', 'mike', 'work')

        self.assertEqual(
            ['~albert/november/work', '~bob/november/work'],
            self._get_merge_proposals(
                getUtility(IProductSet).getByName('november')))

    def test_wip_for_product_restrictions(self):
        # Check queries on product limited on status.
        in_progress = self._make_merge_proposal('albert', 'november', 'work')
        needs_review = self._make_merge_proposal(
            'bob', 'november', 'work', needs_review=True)
        self.assertEqual(
            ['~albert/november/work'],
            self._get_merge_proposals(
                getUtility(IProductSet).getByName('november'),
                status=[BranchMergeProposalStatus.WORK_IN_PROGRESS]))

    def test_all_for_person_restrictions(self):
        # Queries on person should limit results to that person.
        self._make_merge_proposal('albert', 'november', 'work')
        self._make_merge_proposal('albert', 'mike', 'work')
        # And make a proposal for another product to make sure that it doesn't
        # appear
        self._make_merge_proposal('charles', 'mike', 'work')

        self.assertEqual(
            ['~albert/mike/work', '~albert/november/work'],
            self._get_merge_proposals(
                getUtility(IPersonSet).getByName('albert')))

    def test_wip_for_person_restrictions(self):
        # If looking for the merge proposals for a person, and the status is
        # specified, then the resulting proposals will have one of the states
        # specified.
        self._make_merge_proposal('albert', 'november', 'work')
        self._make_merge_proposal(
            'albert', 'november', 'review', needs_review=True)
        self.assertEqual(
            ['~albert/november/work'],
            self._get_merge_proposals(
                getUtility(IPersonSet).getByName('albert'),
                status=[BranchMergeProposalStatus.WORK_IN_PROGRESS]))

    def test_private_branches(self):
        # The resulting list of merge proposals is filtered by the actual
        # proposals that the logged in user is able to see.
        proposal = self._make_merge_proposal('albert', 'november', 'work')
        # Mark the source branch private.
        proposal.source_branch.private = True
        self._make_merge_proposal('albert', 'mike', 'work')

        albert = getUtility(IPersonSet).getByName('albert')
        # Albert can see his private branch.
        self.assertEqual(
            ['~albert/mike/work', '~albert/november/work'],
            self._get_merge_proposals(albert, visible_by_user=albert))
        # Anonymous people can't.
        self.assertEqual(
            ['~albert/mike/work'],
            self._get_merge_proposals(albert))
        # Other people can't.
        self.assertEqual(
            ['~albert/mike/work'],
            self._get_merge_proposals(
                albert, visible_by_user=self.factory.makePerson()))
        # A branch subscribers can.
        subscriber = self.factory.makePerson()
        proposal.source_branch.subscribe(
            subscriber,
            BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.NOEMAIL)
        self.assertEqual(
            ['~albert/mike/work', '~albert/november/work'],
            self._get_merge_proposals(albert, visible_by_user=subscriber))

    def test_team_private_branches(self):
        # If both charles and albert are a member team xray, and albert
        # creates a branch in the team namespace, charles will be able to see
        # it.
        albert = self.factory.makePerson(name='albert')
        charles = self.factory.makePerson(name='charles')
        xray = self.factory.makeTeam(name='xray', owner=albert)
        xray.addMember(person=charles, reviewer=albert)

        proposal = self._make_merge_proposal(
            'xray', 'november', 'work', registrant=albert)
        # Mark the source branch private.
        proposal.source_branch.private = True

        november = getUtility(IProductSet).getByName('november')
        # The proposal is visible to charles.
        self.assertEqual(
            ['~xray/november/work'],
            self._get_merge_proposals(november, visible_by_user=charles))
        # Not visible to anonymous people.
        self.assertEqual([], self._get_merge_proposals(november))
        # Not visible to non team members.
        self.assertEqual(
            [],
            self._get_merge_proposals(
                november, visible_by_user=self.factory.makePerson()))


class TestBranchMergeProposalNominateReviewer(TestCaseWithFactory):
    """Test that the appropriate vote references get created."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self, user='test@canonical.com')

    def test_no_initial_votes(self):
        """A new merge proposal has no votes."""
        merge_proposal = self.factory.makeBranchMergeProposal()
        self.assertEqual([], list(merge_proposal.votes))

    def test_nominate_creates_reference(self):
        """A new vote reference is created when a reviewer is nominated."""
        merge_proposal = self.factory.makeBranchMergeProposal()
        login(merge_proposal.source_branch.owner.preferredemail.email)
        reviewer = self.factory.makePerson()
        merge_proposal.nominateReviewer(
            reviewer=reviewer,
            registrant=merge_proposal.source_branch.owner,
            review_type='General')
        votes = list(merge_proposal.votes)
        self.assertEqual(1, len(votes))
        vote_reference = votes[0]
        self.assertEqual(reviewer, vote_reference.reviewer)
        self.assertEqual(merge_proposal.source_branch.owner,
                         vote_reference.registrant)
        self.assertEqual('General', vote_reference.review_type)

    def test_comment_with_vote_creates_reference(self):
        """A comment with a vote creates a vote reference."""
        merge_proposal = self.factory.makeBranchMergeProposal()
        reviewer = self.factory.makePerson()
        comment = merge_proposal.createComment(
            reviewer, 'Message subject', 'Message content',
            vote=CodeReviewVote.APPROVE)
        votes = list(merge_proposal.votes)
        self.assertEqual(1, len(votes))
        vote_reference = votes[0]
        self.assertEqual(reviewer, vote_reference.reviewer)
        self.assertEqual(reviewer, vote_reference.registrant)
        self.assertTrue(vote_reference.review_type is None)
        self.assertEqual(comment, vote_reference.comment)

    def test_comment_without_a_vote_does_not_create_reference(self):
        """A comment with a vote creates a vote reference."""
        merge_proposal = self.factory.makeBranchMergeProposal()
        reviewer = self.factory.makePerson()
        comment = merge_proposal.createComment(
            reviewer, 'Message subject', 'Message content')
        self.assertEqual([], list(merge_proposal.votes))

    def test_second_vote_by_person_just_alters_reference(self):
        """A second vote changes the comment reference only."""
        merge_proposal = self.factory.makeBranchMergeProposal()
        reviewer = self.factory.makePerson()
        comment1 = merge_proposal.createComment(
            reviewer, 'Message subject', 'Message content',
            vote=CodeReviewVote.DISAPPROVE)
        comment2 = merge_proposal.createComment(
            reviewer, 'Message subject', 'Message content',
            vote=CodeReviewVote.APPROVE)
        votes = list(merge_proposal.votes)
        self.assertEqual(1, len(votes))
        vote_reference = votes[0]
        self.assertEqual(reviewer, vote_reference.reviewer)
        self.assertEqual(reviewer, vote_reference.registrant)
        self.assertTrue(vote_reference.review_type is None)
        self.assertEqual(comment2, vote_reference.comment)

    def test_vote_by_nominated_reuses_reference(self):
        """A comment with a vote for a nominated reviewer alters reference."""
        merge_proposal = self.factory.makeBranchMergeProposal()
        login(merge_proposal.source_branch.owner.preferredemail.email)
        reviewer = self.factory.makePerson()
        merge_proposal.nominateReviewer(
            reviewer=reviewer,
            registrant=merge_proposal.source_branch.owner,
            review_type='General')
        comment = merge_proposal.createComment(
            reviewer, 'Message subject', 'Message content',
            vote=CodeReviewVote.APPROVE)

        votes = list(merge_proposal.votes)
        self.assertEqual(1, len(votes))
        vote_reference = votes[0]
        self.assertEqual(reviewer, vote_reference.reviewer)
        self.assertEqual(merge_proposal.source_branch.owner,
                         vote_reference.registrant)
        self.assertEqual('General', vote_reference.review_type)
        self.assertEqual(comment, vote_reference.comment)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
