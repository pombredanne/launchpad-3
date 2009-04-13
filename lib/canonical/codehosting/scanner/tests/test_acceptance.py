# Copyright 2006-2008 Canonical Ltd.  All rights reserved.
# Author: David Allouche <david@allouche.net>

"""End-to-end tests for the Branch Scanner script."""

__metaclass__ = type


import os
import shutil
from subprocess import Popen, PIPE
from unittest import TestLoader

import bzrlib.branch
from bzrlib.tests import TestCaseWithTransport
from bzrlib.transport import get_transport
from bzrlib.urlutils import local_path_from_url

import transaction
from zope.component import getUtility

from canonical.codehosting.vfs import branch_id_to_path
from canonical.codehosting.bzrutils import ensure_base
from canonical.codehosting.tests.helpers import (
    create_branch_with_one_revision, LoomTestMixin)
from canonical.config import config
from lp.code.interfaces.branchlookup import IBranchLookup
from canonical.testing import ZopelessAppServerLayer


class BranchScannerTest(TestCaseWithTransport, LoomTestMixin):
    """Tests for cronscripts/branch-scanner.py."""

    layer = ZopelessAppServerLayer

    # Branch to install branch-scanner test data on.
    branch_id = 7

    def setUp(self):
        TestCaseWithTransport.setUp(self)
        self.db_branch = getUtility(IBranchLookup).get(self.branch_id)
        assert self.db_branch.revision_history.count() == 0

    def getWarehouseLocation(self, db_branch):
        """Get the warehouse location for a database branch."""
        destination = os.path.join(
            local_path_from_url(
                config.codehosting.internal_branch_by_id_root),
            branch_id_to_path(db_branch.id))
        ensure_base(get_transport(destination))
        self.addCleanup(lambda: shutil.rmtree(destination))
        return destination

    def installTestBranch(self, db_branch, bzr_branch):
        """Tell the DB that the contents of `db_branch` is `bzr_branch`."""
        # record the last mirrored revision
        db_branch.last_mirrored_id = bzr_branch.last_revision()
        transaction.commit()

    def runScanner(self):
        """Run branch-scanner.py and return the outputs.

        The result can be checked using `assertScannerRanOK`.
        """
        script = os.path.join(config.root, 'cronscripts', 'branch-scanner.py')
        process = Popen([script],
                        stdout=PIPE, stderr=PIPE, stdin=open('/dev/null'))
        output, error = process.communicate()
        status = process.returncode
        return status, output, error

    def assertScannerRanOK(self, (status, output, error)):
        """Assert that the scanner script ran OK.

        This script takes the return value of `runScanner` as its only
        parameter.
        """
        self.assertEqual(
            status, 0,
            'branch-scanner.py exited with status=%d\n'
            '>>>stdout<<<\n%s\n>>>stderr<<<\n%s'
            % (status, output, error))

    def test_branchScannerScript(self):
        # Running the scanner script scans branches that have been mirrored
        # recently.
        #
        # This test is more of a smoke test to confirm that the script itself
        # behaves sanely. For more comprehensive tests, see
        # lib/canonical/codehosting/tests/test_scanner_bzrsync.
        destination = self.getWarehouseLocation(self.db_branch)
        bzr_tree = create_branch_with_one_revision(destination)
        self.installTestBranch(self.db_branch, bzr_tree.branch)

        # Run branch-scanner.py and check the process outputs.
        result = self.runScanner()
        self.assertScannerRanOK(result)

        # Check that all branches were set to the test data.
        transaction.abort()
        history = self.db_branch.revision_history
        self.assertEqual(history.count(), 1)
        revision = history[0].revision
        self.assertEqual(revision.log_body, 'message')

    def test_branchScannerLooms(self):
        # The branch scanner can scan loomified branches.
        destination = self.getWarehouseLocation(self.db_branch)

        # Build the loom in the destination directory.
        self.addCleanup(lambda: os.chdir(os.getcwd()))
        os.chdir(destination)
        loom_tree = self.makeLoomBranchAndTree('.')

        loom_branch = bzrlib.branch.Branch.open(destination)
        self.installTestBranch(self.db_branch, loom_branch)

        # Run branch-scanner.py and check the process outputs.
        result = self.runScanner()
        self.assertScannerRanOK(result)

        # Check that all branches were set to the test data.
        transaction.abort()
        history = self.db_branch.revision_history
        self.assertEqual(history.count(), 1)



def test_suite():
    return TestLoader().loadTestsFromName(__name__)
