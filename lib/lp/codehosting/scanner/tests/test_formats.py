# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for how the scanner processes Bazaar formats."""

__metaclass__ = type

import unittest

from lp.codehosting.scanner.tests.test_bzrsync import BzrSyncTestCase
from lp.code.interfaces.branch import (
    BranchFormat, ControlFormat, RepositoryFormat)


class TestScanFormatPack(BzrSyncTestCase):
    """Test scanning of pack-format repositories."""

    def testRecognizePack(self):
        """Ensure scanner records correct formats for pack branches."""
        self.makeBzrSync(self.db_branch).syncBranchAndClose()
        self.assertEqual(self.db_branch.branch_format,
                         BranchFormat.BZR_BRANCH_6)
        self.assertEqual(self.db_branch.repository_format,
                         RepositoryFormat.BZR_KNITPACK_1)
        self.assertEqual(self.db_branch.control_format,
                         ControlFormat.BZR_METADIR_1)


class TestScanFormatKnit(BzrSyncTestCase):
    """Test scanning of knit-format repositories."""

    def makeBzrBranchAndTree(self, db_branch):
        return BzrSyncTestCase.makeBzrBranchAndTree(self, db_branch, 'knit')

    def testRecognizeKnit(self):
        """Ensure scanner records correct formats for knit branches."""
        self.makeBzrSync(self.db_branch).syncBranchAndClose()
        self.assertEqual(self.db_branch.branch_format,
                         BranchFormat.BZR_BRANCH_5)


class TestScanBranchFormat7(BzrSyncTestCase):
    """Test scanning of format 7 (i.e. stacking-supporting) branches."""

    def makeBzrBranchAndTree(self, db_branch):
        return BzrSyncTestCase.makeBzrBranchAndTree(
            self, db_branch, '1.6')

    def testRecognizeDevelopment(self):
        """Ensure scanner records correct format for development branches."""
        self.makeBzrSync(self.db_branch).syncBranchAndClose()
        self.assertEqual(
            self.db_branch.branch_format, BranchFormat.BZR_BRANCH_7)


class TestScanFormatWeave(BzrSyncTestCase):
    """Test scanning of weave-format branches.

    Weave is an "all-in-one" format, where branch, repo and tree formats are
    implied by the control directory format."""

    def makeBzrBranchAndTree(self, db_branch):
        return BzrSyncTestCase.makeBzrBranchAndTree(self, db_branch, 'weave')

    def testRecognizeWeave(self):
        """Ensure scanner records correct weave formats."""
        self.makeBzrSync(self.db_branch).syncBranchAndClose()
        self.assertEqual(self.db_branch.branch_format,
                         BranchFormat.BZR_BRANCH_4)
        self.assertEqual(self.db_branch.repository_format,
                         RepositoryFormat.BZR_REPOSITORY_6)
        self.assertEqual(self.db_branch.control_format,
                         ControlFormat.BZR_DIR_6)


class TestScanUnrecognizedFormat(BzrSyncTestCase):
    """Test scanning unrecognized formats"""

    def testUnrecognize(self):
        """Scanner should record UNRECOGNIZED for all format values."""
        class MockFormat:
            def get_format_string(self):
                return 'Unrecognizable'

        class MockWithFormat:
            def __init__(self):
                self._format = MockFormat()

        class MockBranch(MockWithFormat):
            bzrdir = MockWithFormat()
            repository = MockWithFormat()

        branch = MockBranch()
        self.makeBzrSync(self.db_branch).setFormats(branch)
        self.assertEqual(self.db_branch.branch_format,
                         BranchFormat.UNRECOGNIZED)
        self.assertEqual(self.db_branch.repository_format,
                         RepositoryFormat.UNRECOGNIZED)
        self.assertEqual(self.db_branch.control_format,
                         ControlFormat.UNRECOGNIZED)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

