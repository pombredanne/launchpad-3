#! /usr/bin/python2.5
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the scan_branches script."""


import transaction

from canonical.testing import ZopelessAppServerLayer
from lp.testing import TestCaseWithFactory
from canonical.launchpad.scripts.tests import run_script
from lp.code.model.branchjob import BranchScanJob


class TestScanBranches(TestCaseWithFactory):
    """Test the scan_branches script."""

    layer = ZopelessAppServerLayer

    def make_branch_with_commits_and_scan_job(self, db_branch):
        """Create a branch from a db_branch, make commits and a scan job."""
        target, target_tree = self.create_branch_and_tree(
            db_branch=db_branch)
        target_tree.commit('First commit', rev_id='rev1')
        target_tree.commit('Second commit', rev_id='rev2')
        target_tree.commit('Third commit', rev_id='rev3')
        job = BranchScanJob.create(db_branch)
        transaction.commit()

    def run_script_and_assert_success(self):
        """Run the scan_branches script and assert it ran successfully."""
        retcode, stdout, stderr = run_script(
            'cronscripts/scan_branches.py', [],
            expect_returncode=0)
        self.assertEqual('', stdout)
        self.assertIn(
            'INFO    Ran 1 IBranchScanJobSource jobs.\n', stderr)

    def test_scan_branch(self):
        """Test that scan branches adds revisions to the database."""
        self.useBzrBranches(real_server=True)

        db_branch = self.factory.makeAnyBranch()
        self.make_branch_with_commits_and_scan_job(db_branch)

        self.run_script_and_assert_success()
        self.assertEqual(db_branch.revision_count, 3)

    def test_scan_branch_packagebranch(self):
        """Test that scan_branches can scan package branches."""
        self.useBzrBranches(real_server=True)

        db_branch = self.factory.makePackageBranch()
        self.make_branch_with_commits_and_scan_job(db_branch)

        self.run_script_and_assert_success()
        self.assertEqual(db_branch.revision_count, 3)
