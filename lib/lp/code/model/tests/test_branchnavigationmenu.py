# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for IBranchNavigationMenu implementations"""

__metaclass__ = type

from unittest import TestLoader

from lp.code.interfaces.branch import IBranchNavigationMenu
from lp.testing import TestCaseWithFactory
from canonical.testing import LaunchpadZopelessLayer


class TestBranchNavigation(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_simple_branch(self):
        """Branches implement IBranchNavigation"""
        branch = self.factory.makeAnyBranch()
        self.assertTrue(IBranchNavigationMenu.providedBy(branch))

    def test_merge_proposal(self):
        """Merge proposals implement IBranchNavigation"""
        merge_proposal = self.factory.makeBranchMergeProposal()
        self.assertTrue(IBranchNavigationMenu.providedBy(merge_proposal))

    def test_branch_subscription(self):
        """Branch subscriptions implement IBranchNavigation"""
        subscription = self.factory.makeBranchSubscription()
        self.assertTrue(IBranchNavigationMenu.providedBy(subscription))

    def test_review_comment(self):
        """Review comments implement IBranchNavigation"""
        comment = self.factory.makeCodeReviewComment()
        self.assertTrue(IBranchNavigationMenu.providedBy(comment))


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

