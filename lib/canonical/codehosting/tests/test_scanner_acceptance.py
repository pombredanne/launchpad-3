# Copyright 2006-2008 Canonical Ltd.  All rights reserved.
# Author: David Allouche <david@allouche.net>

"""End-to-end tests for the Branch Scanner script."""

__metaclass__ = type


import os
from os.path import join, isdir, exists
from shutil import rmtree
from subprocess import Popen, PIPE
import tempfile
from unittest import TestCase, TestLoader

import bzrlib.branch

import transaction
from zope.component import getUtility

from canonical.codehosting.tests.helpers import (
    create_branch_with_one_revision)
from canonical.config import config
from canonical.launchpad.interfaces import IBranchSet
from canonical.testing import LaunchpadZopelessLayer


class BranchScannerTest(TestCase):
    """Branch to install branch-scanner test data on."""

    layer = LaunchpadZopelessLayer
    branch_id = 7

    def setUp(self):
        TestCase.setUp(self)
        # Clear the HOME environment variable in order to ignore existing
        # user config files.
        self.testdir = tempfile.mkdtemp()
        self._saved_environ = dict(os.environ)
        os.environ['HOME'] = self.testdir
        self.setUpWarehouse()
        self.db_branch = getUtility(IBranchSet)[self.branch_id]
        assert self.db_branch.revision_history.count() == 0

    def tearDown(self):
        rmtree(self.testdir)
        os.environ.clear()
        os.environ.update(self._saved_environ)
        TestCase.tearDown(self)

    def setUpWarehouse(self):
        """Create a sandbox branch warehouse for testing.

        See doc/bazaar for more context on the branch warehouse concept.
        """
        warehouse_url = config.supermirror.warehouse_root_url
        assert warehouse_url.startswith('file://')
        warehouse = warehouse_url[len('file://'):]
        if isdir(warehouse):
            rmtree(warehouse)
        os.mkdir(warehouse)
        self.warehouse = warehouse

    def getWarehouseLocation(self, db_branch):
        """Get the warehouse location for a database branch."""
        destination = join(self.warehouse, '%08x' % db_branch.id)
        assert not exists(destination)
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
        script = join(config.root, 'cronscripts', 'branch-scanner.py')
        process = Popen([script, '-q'],
                        stdout=PIPE, stderr=PIPE, stdin=open('/dev/null'))
        output, error = process.communicate()
        status = process.returncode
        return status, output, error

    def assertScannerRanOK(self, (status, output, error)):
        """Assert that the scanner script ran OK.

        This script takes the return value of `runScanner` as its only
        parameter.
        """
        self.assertEqual(status, 0,
                         'baz2bzr exited with status=%d\n'
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


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
