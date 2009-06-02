# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for BugBranches."""

__metaclass__ = type

import unittest

from lp.testing import login_person, TestCaseWithFactory
from canonical.launchpad.webapp.interfaces import IPrimaryContext
from canonical.testing import DatabaseFunctionalLayer


class TestBugBranchPrimaryContext(TestCaseWithFactory):
    # Tests the adaptation of a bug branch link into a primary context.

    layer = DatabaseFunctionalLayer

    def testPrimaryContext(self):
        # The primary context of a bug branch link is the same as the
        # primary context of the branch that is linked to the bug.
        branch = self.factory.makeProductBranch()
        bug = self.factory.makeBug(product=branch.product)
        login_person(branch.owner)
        bugbranch = bug.addBranch(branch, branch.owner)
        self.assertEqual(
            IPrimaryContext(bugbranch).context,
            IPrimaryContext(bugbranch.branch).context)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
