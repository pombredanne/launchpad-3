# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for the branch scanner utility."""

__metaclass__ = type

import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.code.interfaces.branch import BranchType
from lp.code.interfaces.branchscanner import IBranchScanner
from lp.testing import TestCaseWithFactory
from canonical.launchpad.testing.databasehelpers import (
    remove_all_sample_data_branches)
from canonical.testing.layers import DatabaseFunctionalLayer


class TestBranchScanner(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        remove_all_sample_data_branches()
        self.scanner = getUtility(IBranchScanner)

    def test_empty(self):
        # If there are no branches, the list of branches to scan is empty.
        self.assertEqual([], list(self.scanner.getBranchesToScan()))

    def test_not_ready_to_scan_by_default(self):
        # Even after we create branches, there's still nothing to scan.
        self.factory.makeAnyBranch()
        self.assertEqual([], list(self.scanner.getBranchesToScan()))

    def test_ready_to_scan_if_mirrored(self):
        # Once a branch has been mirrored, it's ready to scan.
        branch = self.factory.makeAnyBranch()
        branch.startMirroring()
        branch.mirrorComplete('mirrored-rev')
        self.assertEqual([branch], list(self.scanner.getBranchesToScan()))

    def test_once_scanned_no_longer_ready(self):
        # Once a branch has been mirrored, then scanned again, it's no longer
        # in the list of branches to scan.
        branch = self.factory.makeAnyBranch()
        branch.startMirroring()
        branch.mirrorComplete('mirrored-rev')
        revision = self.factory.makeRevision(rev_id='mirrored-rev')
        branch.updateScannedDetails(revision, self.factory.getUniqueInteger())
        self.assertEqual([], list(self.scanner.getBranchesToScan()))

    def test_no_op_mirror_not_ready_to_scan(self):
        # If a branch is mirrored after it's scanned, but the tip revision
        # doesn't change, then it's still not considered ready to scan.
        branch = self.factory.makeAnyBranch()
        branch.startMirroring()
        branch.mirrorComplete('mirrored-rev')
        revision = self.factory.makeRevision(rev_id='mirrored-rev')
        branch.updateScannedDetails(revision, self.factory.getUniqueInteger())
        branch.startMirroring()
        branch.mirrorComplete('mirrored-rev')
        self.assertEqual([], list(self.scanner.getBranchesToScan()))

    def test_remirror_ready_to_scan(self):
        # If a branch is mirrored after it's scanned, but the tip revision
        # *does* change, then it's considered ready to scan.
        branch = self.factory.makeAnyBranch()
        branch.startMirroring()
        branch.mirrorComplete('mirrored-rev')
        revision = self.factory.makeRevision(rev_id='mirrored-rev')
        branch.updateScannedDetails(revision, self.factory.getUniqueInteger())
        branch.startMirroring()
        branch.mirrorComplete('new-rev')
        self.assertEqual([branch], list(self.scanner.getBranchesToScan()))

    def test_scanned_but_not_mirrored(self):
        # If a branch is somehow scanned but never actually mirrored --
        # shouldn't be possible -- then don't include that branch in the
        # branches to scan.
        branch = self.factory.makeAnyBranch()
        revision = self.factory.makeRevision(rev_id='mirrored-rev')
        branch.updateScannedDetails(revision, self.factory.getUniqueInteger())
        self.assertEqual([], list(self.scanner.getBranchesToScan()))

    def test_dont_scan_remote_branches(self):
        # Remote branches have only metadata, and so should never be scanned.
        # Technically they should never be mirrored either.
        branch = self.factory.makeAnyBranch(branch_type=BranchType.REMOTE)
        # Since 'startMirroring' quite rightly borks on remote branches,
        # fiddle with its internals.
        removeSecurityProxy(branch).last_mirrored_id = 'mirrored-rev'
        self.assertEqual([], list(self.scanner.getBranchesToScan()))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
