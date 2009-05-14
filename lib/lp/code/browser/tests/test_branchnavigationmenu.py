# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for BranchNavigationMenu."""

__metaclass__ = type

import unittest

from lp.code.browser.branch import BranchNavigationMenu
from lp.testing import TestCaseWithFactory
from canonical.testing import LaunchpadFunctionalLayer


class TestBranchNavigationMenu(TestCaseWithFactory):
    """Test that the associated branch for the navigation menu are correct."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self, 'test@canonical.com')

    def test_simple_branch(self):
        """Menu's branch should be the branch that the menu is created with"""
        branch = self.factory.makeAnyBranch()
        menu = BranchNavigationMenu(branch)
        self.assertEqual(branch, menu.branch)

    def test_merge_proposal(self):
        """Menu's branch for a proposed merge should be the source branch."""
        proposal = self.factory.makeBranchMergeProposal()
        menu = BranchNavigationMenu(proposal)
        self.assertEqual(proposal.source_branch, menu.branch)

    def test_branch_subscription(self):
        """Menu's branch for a subscription is the branch of the subscription.
        """
        subscription = self.factory.makeBranchSubscription()
        menu = BranchNavigationMenu(subscription)
        self.assertEqual(subscription.branch, menu.branch)

    def test_review_comment(self):
        """Menu's branch for a review comment is the source branch"""
        comment = self.factory.makeCodeReviewComment()
        menu = BranchNavigationMenu(comment)
        self.assertEqual(comment.branch_merge_proposal.source_branch,
            menu.branch)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
