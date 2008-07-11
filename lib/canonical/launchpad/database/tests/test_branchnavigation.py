# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests for Branches."""

__metaclass__ = type

from unittest import TestCase, TestLoader

from canonical.launchpad.ftests import login
from canonical.launchpad.interfaces.branch import IBranchNavigationMenu
from canonical.launchpad.testing import LaunchpadObjectFactory

from canonical.testing import LaunchpadZopelessLayer


class TestBranchNavigation(TestCase):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        login('test@canonical.com')
        self.factory = LaunchpadObjectFactory()

    def test_branchNavInterfaces(self):
        """Tests that proper database classes implement IBranchNavigation"""
        branch = self.factory.makeBranch()
        self.assertTrue(IBranchNavigationMenu.providedBy(branch))
        merge_proposal = self.factory.makeBranchMergeProposal()
        self.assertTrue(IBranchNavigationMenu.providedBy(merge_proposal))
        code_review_comment = self.factory.makeCodeReviewComment()
        self.assertTrue(IBranchNavigationMenu.providedBy(code_review_comment))


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

