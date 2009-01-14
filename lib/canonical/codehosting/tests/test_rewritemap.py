# Copyright 2005-2008 Canonical Ltd.  All rights reserved.

"""Librarian garbage collection tests"""

__metaclass__ = type

from StringIO import StringIO
from unittest import TestLoader

from canonical.codehosting.branchfs import branch_id_to_path
from canonical.launchpad.interfaces import BranchType
from canonical.launchpad.testing import LaunchpadObjectFactory, TestCase
from canonical.codehosting import rewritemap
from canonical.testing import LaunchpadZopelessLayer


class TestRewriteMapScript(TestCase):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.factory = LaunchpadObjectFactory()

    def assertInRewriteMap(self, branch):
        """Assert that `branch` is published in the rewritemap."""
        expected_line = '%s\t%s' % (
            branch.unique_name, branch_id_to_path(branch.id))
        lines = self.getRewriteFileLines()
        self.assertIn(expected_line, lines)

    def assertNotInRewriteMap(self, branch):
        """Assert that `branch` is not published in the rewritemap."""
        expected_line = '%s\t%s' % (
            branch.unique_name, branch_id_to_path(branch.id))
        lines = self.getRewriteFileLines()
        self.assertNotIn(expected_line, lines)

    def getRewriteFileLines(self):
        """Create the rewrite file and return the contents."""
        file = StringIO()
        rewritemap.write_map(file)
        return file.getvalue().splitlines()

    def testFileGeneration(self):
        # A simple smoke test for the rewritemap cronscript.
        branch = self.factory.makeProductBranch()
        self.assertInRewriteMap(branch)

    def testFileGenerationJunkProduct(self):
        # Like test_file_generation, but demonstrating a +junk product.
        branch = self.factory.makePersonalBranch()
        self.assertInRewriteMap(branch)

    def testPrivateBranchNotWritten(self):
        # Private branches do not have entries in the rewrite file.
        branch = self.factory.makeAnyBranch(private=True)
        self.assertNotInRewriteMap(branch)

    def testPrivateStackedBranch(self):
        # Branches stacked on private branches don't have entries in the
        # rewrite file.
        stacked_on_branch = self.factory.makeAnyBranch(private=True)
        stacked_branch = self.factory.makeAnyBranch(
            stacked_on=stacked_on_branch)
        branch_name = stacked_branch.unique_name
        branch_id = stacked_branch.id
        self.assertNotInRewriteMap(stacked_branch)

    def testRemoteBranchNotWritten(self):
        # Remote branches do not have entries in the rewrite file.
        branch = self.factory.makeAnyBranch(BranchType.REMOTE)
        self.assertNotInRewriteMap(branch)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

