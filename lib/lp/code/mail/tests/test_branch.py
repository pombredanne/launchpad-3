# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for Branch-related mailings"""

from unittest import TestLoader

from canonical.testing import DatabaseFunctionalLayer

from canonical.launchpad.database import Branch
from canonical.launchpad.ftests import login_person
from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel, CodeReviewNotificationLevel)
from lp.code.mail.branch import RecipientReason
from canonical.launchpad.testing import TestCaseWithFactory


class TestRecipientReason(TestCaseWithFactory):
    """Test the RecipientReason class."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Need to set target_branch.date_last_modified.
        TestCaseWithFactory.setUp(self, user='test@canonical.com')

    def makeProposalWithSubscription(self, subscriber=None):
        """Test fixture."""
        if subscriber is None:
            subscriber = self.factory.makePerson()
        source_branch = self.factory.makeProductBranch(title='foo')
        target_branch = self.factory.makeProductBranch(
            product=source_branch.product, title='bar')
        merge_proposal = source_branch.addLandingTarget(
            source_branch.owner, target_branch)
        subscription = merge_proposal.source_branch.subscribe(
            subscriber, BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.FULL)
        return merge_proposal, subscription

    def test_forBranchSubscriber(self):
        """Test values when created from a branch subscription."""
        merge_proposal, subscription = self.makeProposalWithSubscription()
        subscriber = subscription.person
        reason = RecipientReason.forBranchSubscriber(
            subscription, subscriber, '', merge_proposal)
        self.assertEqual(subscriber, reason.subscriber)
        self.assertEqual(subscriber, reason.recipient)
        self.assertEqual(merge_proposal.source_branch, reason.branch)

    def makeReviewerAndSubscriber(self):
        """Return a tuple of vote_reference, subscriber."""
        merge_proposal, subscription = self.makeProposalWithSubscription()
        subscriber = subscription.person
        login_person(merge_proposal.registrant)
        vote_reference = merge_proposal.nominateReviewer(
            subscriber, subscriber)
        return merge_proposal, vote_reference, subscriber

    def test_forReviewer(self):
        """Test values when created from a branch subscription."""
        ignored, vote_reference, subscriber = self.makeReviewerAndSubscriber()
        reason = RecipientReason.forReviewer(vote_reference, subscriber)
        self.assertEqual(subscriber, reason.subscriber)
        self.assertEqual(subscriber, reason.recipient)
        self.assertEqual(
            vote_reference.branch_merge_proposal.source_branch, reason.branch)

    def test_getReasonReviewer(self):
        bmp, vote_reference, subscriber = self.makeReviewerAndSubscriber()
        reason = RecipientReason.forReviewer(vote_reference, subscriber)
        self.assertEqual(
            'You are requested to review the proposed merge of %s into %s.'
            % (bmp.source_branch.bzr_identity,
               bmp.target_branch.bzr_identity),
            reason.getReason())

    def test_getReasonPerson(self):
        """Ensure the correct reason is generated for individuals."""
        merge_proposal, subscription = self.makeProposalWithSubscription()
        reason = RecipientReason.forBranchSubscriber(
            subscription, subscription.person, '', merge_proposal)
        self.assertEqual(
            'You are subscribed to branch %s.'
            % merge_proposal.source_branch.bzr_identity, reason.getReason())

    def test_getReasonTeam(self):
        """Ensure the correct reason is generated for teams."""
        team_member = self.factory.makePerson(
            displayname='Foo Bar', email='foo@bar.com')
        team = self.factory.makeTeam(team_member, displayname='Qux')
        bmp, subscription = self.makeProposalWithSubscription(team)
        reason = RecipientReason.forBranchSubscriber(
            subscription, team_member, '', bmp)
        self.assertEqual(
            'Your team Qux is subscribed to branch %s.'
            % bmp.source_branch.bzr_identity, reason.getReason())

    def test_usesBranchIdentityCache(self):
        """Ensure that the cache is used for branches if provided."""
        branch = self.factory.makeAnyBranch()
        subscription = branch.getSubscription(branch.owner)
        branch_cache = {branch: 'lp://fake'}
        def blowup(self):
            raise AssertionError('boom')
        patched = Branch.bzr_identity
        Branch.bzr_identity = property(blowup)
        def cleanup():
            Branch.bzr_identity = patched
        self.addCleanup(cleanup)
        self.assertRaises(AssertionError, getattr, branch, 'bzr_identity')
        reason = RecipientReason.forBranchSubscriber(
            subscription, subscription.person, '',
            branch_identity_cache=branch_cache)
        self.assertEqual(
            'You are subscribed to branch lp://fake.',
            reason.getReason())


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
