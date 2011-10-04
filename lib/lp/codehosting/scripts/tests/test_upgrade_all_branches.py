# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


import os.path
import logging

from bzrlib.repofmt.groupcompress_repo import RepositoryFormat2a
import transaction

from canonical.testing.layers import AppServerLayer
from lp.code.bzr import branch_changed
from lp.codehosting.upgrade import Upgrader
from lp.testing import (
    person_logged_in,
    run_script,
    TestCaseWithFactory,
    )


class TestUpgradeAllBranchesScript(TestCaseWithFactory):

    layer = AppServerLayer

    def setUp(self):
        super(TestUpgradeAllBranchesScript, self).setUp()
        # useBzrBranches changes cwd
        self.cwd = os.getcwd()

    def upgrade_all_branches(self, target, finish=False):
        transaction.commit()
        if finish:
            flags = ' --finish '
        else:
            flags = ' '
        return run_script(
            'scripts/upgrade_all_branches.py' + flags + target, cwd=self.cwd)

    def prepare(self):
        self.useBzrBranches(direct_database=True)
        branch, tree = self.create_branch_and_tree(format='pack-0.92')
        tree.commit('foo')
        with person_logged_in(branch.owner):
            branch_changed(branch, tree.branch)
        target = self.makeTemporaryDirectory()
        upgrader = Upgrader(branch, target, logging.getLogger(), tree.branch)
        return upgrader

    def test_start_upgrade(self):
        upgrader = self.prepare()
        stdout, stderr, retcode = self.upgrade_all_branches(
            upgrader.target_dir)
        self.assertIn(
            'INFO    Upgrading branch %s' % upgrader.branch.unique_name,
            stderr)
        self.assertIn(
            'INFO    Converting repository with fetch.', stderr)
        self.assertIn(
            'INFO    Skipped 0 already-upgraded branches.', stderr)
        self.assertEqual(0, retcode)
        upgraded = upgrader.get_bzrdir().open_repository()
        self.assertIs(RepositoryFormat2a, upgraded._format.__class__)

    def test_finish_upgrade(self):
        upgrader = self.prepare()
        upgrader.start_upgrade()
        stdout, stderr, retcode = self.upgrade_all_branches(
            upgrader.target_dir, finish=True)
        self.assertIn(
            'INFO    Upgrading branch %s' % upgrader.branch.unique_name,
            stderr)
        self.assertEqual(0, retcode)
        upgraded = upgrader.branch.getBzrBranch()
        self.assertIs(
            RepositoryFormat2a, upgraded.repository._format.__class__)
