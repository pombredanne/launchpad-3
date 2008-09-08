# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for karma allocated for code reviews."""

__metaclass__ = type

from unittest import TestLoader

from canonical.launchpad.event.interfaces import IKarmaAssignedEvent
from canonical.launchpad.ftests import login_person
from canonical.launchpad.ftests.event import TestEventListener
from canonical.launchpad.interfaces.person import IPerson
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.testing import DatabaseFunctionalLayer


class TestCodeReviewKarma(TestCaseWithFactory):
    """Test the allocation of karma for revisions."""

    layer = DatabaseFunctionalLayer
    karma_listener = None

    def setUp(self):
        # Use an administrator to set branch privacy easily.
        TestCaseWithFactory.setUp(self, "admin@canonical.com")

        # The way the zope infrastructure works is that we can register
        # subscribers easily, but there is no way to unregister them
        # (bug 2338).
        # The TestEventListener does this with by setting a property to
        # stop calling the callback function.  Instead of ending up with a
        # whole pile of registered inactive event listeners, we just reactive
        # the one we have if there is one.
        if self.karma_listener is None:
            self.karma_listener = TestEventListener(
                IPerson, IKarmaAssignedEvent, self._on_karma_assigned)
        else:
            self.karma_listener._active = True

        self.karma_events = []

    def tearDown(self):
        self.karma_listener.unregister()

    def _on_karma_assigned(self, object, event):
        # Store the karma event for checking in the test method.
        self.karma_events.append(event.karma)

    def test_mergeProposalCreationAllocatesKarma(self):
        # We need to clear the karma event list before we add the landing
        # target as there would be other karma events for the branch
        # creations.
        source_branch = self.factory.makeBranch()
        target_branch = self.factory.makeBranch(product=source_branch.product)
        registrant = self.factory.makePerson()
        self.karma_events = []
        # The normal SQLObject events use the logged in person.
        login_person(registrant)
        source_branch.addLandingTarget(registrant, target_branch)
        [event] = self.karma_events
        self.assertEqual(registrant, event.person)
        self.assertEqual('branchmergeproposed', event.action.name)

    def test_commentOnProposal(self):
        # Any person commenting on a code review gets a karma event.
        proposal = self.factory.makeBranchMergeProposal()
        commenter = self.factory.makePerson()
        self.karma_events = []
        login_person(commenter)
        proposal.createComment(commenter, "A comment", "The review.")
        [event] = self.karma_events
        self.assertEqual(commenter, event.person)
        self.assertEqual('codereviewcomment', event.action.name)

    def test_reviewerCommentingOnProposal(self):
        # A reviewer commenting on a code review gets a different karma event
        # to non-reviewers commenting.
        proposal = self.factory.makeBranchMergeProposal()
        commenter = proposal.target_branch.owner
        self.karma_events = []
        login_person(commenter)
        proposal.createComment(commenter, "A comment", "The review.")
        [event] = self.karma_events
        self.assertEqual(commenter, event.person)
        self.assertEqual('codereviewreviewercomment', event.action.name)

    def test_commentOnOwnProposal(self):
        # If the reviewer is also the registrant of the proposal, they just
        # get a normal code review comment karma event.
        commenter = self.factory.makePerson()
        target_branch = self.factory.makeBranch(owner=commenter)
        proposal = self.factory.makeBranchMergeProposal(
            target_branch=target_branch, registrant=commenter)
        self.karma_events = []
        login_person(commenter)
        proposal.createComment(commenter, "A comment", "The review.")
        [event] = self.karma_events
        self.assertEqual(commenter, event.person)
        self.assertEqual('codereviewcomment', event.action.name)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
