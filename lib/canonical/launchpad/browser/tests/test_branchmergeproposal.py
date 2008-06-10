# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Unit tests for BranchMergeProposals."""

__metaclass__ = type

from datetime import timedelta
import unittest

from canonical.launchpad.browser.branchmergeproposal import (
    BranchMergeProposalVoteView)
from canonical.launchpad.interfaces.codereviewcomment import (
    CodeReviewVote)
from canonical.launchpad.testing import TestCaseWithFactory, time_counter
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import LaunchpadFunctionalLayer


class TestBranchMergeProposalVoteView(TestCaseWithFactory):
    """Make sure that the votes are returned in the right order."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        # Use an admin so we don't have to worry about launchpad.Edit
        # permissions on the merge proposals for adding comments, or
        # nominating reviewers.
        TestCaseWithFactory.setUp(self, user="foo.bar@canonical.com")
        self.bmp = self.factory.makeBranchMergeProposal()

    def testNoVotes(self):
        # No votes should return empty lists
        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())
        self.assertEqual([], view.current_reviews)
        self.assertEqual([], view.requested_reviews)

    def testRequestedOrdering(self):
        # No votes should return empty lists
        date_generator = time_counter(delta=timedelta(days=1))
        # Request three reviews.
        albert = self.factory.makePerson(name='albert')
        bob = self.factory.makePerson(name='bob')
        charles = self.factory.makePerson(name='charles')

        owner = self.bmp.source_branch.owner

        review1 = self.bmp.nominateReviewer(
            reviewer=albert, registrant=owner,
            _date_created=date_generator.next())
        review2 = self.bmp.nominateReviewer(
            reviewer=bob, registrant=owner,
            _date_created=date_generator.next())
        review3 = self.bmp.nominateReviewer(
            reviewer=charles, registrant=owner,
            _date_created=date_generator.next())

        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())
        self.assertEqual([], view.current_reviews)
        requested_reviews = view.requested_reviews
        self.assertEqual(3, len(requested_reviews))
        self.assertEqual([charles, bob, albert],
                         [review.reviewer for review in requested_reviews])

    def testCurrentReviewOrdering(self):
        # Disapprove first, then Approve, lastly Abstain.
        date_generator = time_counter(delta=timedelta(days=1))
        # Request three reviews.
        albert = self.factory.makePerson(name='albert')
        bob = self.factory.makePerson(name='bob')
        charles = self.factory.makePerson(name='charles')

        owner = self.bmp.source_branch.owner

        comment1 = self.bmp.createComment(
            owner=albert, subject=self.factory.getUniqueString('subject'),
            vote=CodeReviewVote.APPROVE)
        comment2 = self.bmp.createComment(
            owner=bob, subject=self.factory.getUniqueString('subject'),
            vote=CodeReviewVote.ABSTAIN)
        comment3 = self.bmp.createComment(
            owner=charles, subject=self.factory.getUniqueString('subject'),
            vote=CodeReviewVote.DISAPPROVE)

        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())

        self.assertEqual([charles, albert, bob],
                         [review.reviewer for review in view.current_reviews])

    def testChangeOfVoteBringsToTop(self):
        # If albert changes his abstention to an approve, it comes before
        # other votes that occurred between the abstention and the approval.

        # Disapprove first, then Approve, lastly Abstain.
        date_generator = time_counter(delta=timedelta(days=1))
        # Request three reviews.
        albert = self.factory.makePerson(name='albert')
        bob = self.factory.makePerson(name='bob')

        owner = self.bmp.source_branch.owner

        comment1 = self.bmp.createComment(
            owner=albert, subject=self.factory.getUniqueString('subject'),
            vote=CodeReviewVote.ABSTAIN, _date_created=date_generator.next())
        comment2 = self.bmp.createComment(
            owner=bob, subject=self.factory.getUniqueString('subject'),
            vote=CodeReviewVote.APPROVE, _date_created=date_generator.next())
        comment3 = self.bmp.createComment(
            owner=albert, subject=self.factory.getUniqueString('subject'),
            vote=CodeReviewVote.APPROVE, _date_created=date_generator.next())

        view = BranchMergeProposalVoteView(self.bmp, LaunchpadTestRequest())

        self.assertEqual([albert, bob],
                         [review.reviewer for review in view.current_reviews])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
