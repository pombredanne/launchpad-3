# Copyright 2006 Canonical Ltd.  All rights reserved.
# Author: David Allouche <david@allouche.net>

"""Feature tests for the Branch Scanner script."""

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

from canonical.config import config
from canonical.launchpad.interfaces import IBranchSet
from canonical.launchpad.scripts.supermirror.tests import createbranch
from canonical.testing import LaunchpadZopelessLayer


class BranchScannerTest(TestCase):
    layer = LaunchpadZopelessLayer
    branch_id = 7
    """Branch to install branch-scanner test data on."""

    def setUp(self):
        TestCase.setUp(self)
        # Clear the HOME environment variable in order to ignore existing
        # user config files.
        self.testdir = tempfile.mkdtemp()
        self._saved_environ = dict(os.environ)
        os.environ['HOME'] = self.testdir
        self.warehouse = None

    def tearDown(self):
        rmtree(self.testdir)
        os.environ.clear()
        os.environ.update(self._saved_environ)
        TestCase.tearDown(self)

    def setupWarehouse(self):
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

    def installTestBranch(self, db_branch):
        """Create a test data in the warehouse for the given branch object."""
        destination = join(self.warehouse, '%08x' % db_branch.id)
        assert not exists(destination)
        createbranch(destination)
        # record the last mirrored revision
        bzr_branch = bzrlib.branch.Branch.open(destination)
        db_branch.last_mirrored_id = bzr_branch.last_revision()

    def test_branch_scanner_script(self):
        # this test checks that branch-scanner.py does something
        self.setupWarehouse()
        branch = getUtility(IBranchSet)[self.branch_id]
        assert branch.revision_history.count() == 0
        self.installTestBranch(branch)
        transaction.commit()
        # run branch-scanner.py and check the process outputs
        script = join(config.root, 'cronscripts', 'branch-scanner.py')
        process = Popen([script, '-q'],
                        stdout=PIPE, stderr=PIPE, stdin=open('/dev/null'))
        output, error = process.communicate()
        status = process.returncode
        self.assertEqual(status, 0,
                         'baz2bzr exited with status=%d\n'
                         '>>>stdout<<<\n%s\n>>>stderr<<<\n%s'
                         % (status, output, error))
        # check that all branches were set to the test data
        transaction.abort()
        history = branch.revision_history
        self.assertEqual(history.count(), 1)
        revision = history[0].revision
        self.assertEqual(revision.log_body, 'message')


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
