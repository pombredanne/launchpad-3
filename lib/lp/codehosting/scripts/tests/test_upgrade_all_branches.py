# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


import os.path

import transaction

from canonical.testing.layers import AppServerLayer
from lp.code.bzr import (
    branch_changed,
    get_branch_formats,
    )
from lp.testing import (
    person_logged_in,
    run_script,
    TestCaseWithFactory,
    )
from lp.codehosting.upgrade import Upgrader


class TestUpgradeAllBranchesScript(TestCaseWithFactory):

    layer = AppServerLayer

    def setUp(self):
        super(TestUpgradeAllBranchesScript, self).setUp()
        # useBzrBranches changes cwd
        self.cwd = os.getcwd()

    def upgrade_all_branches(self, target):
        transaction.commit()
        return run_script(
            'scripts/upgrade_all_branches.py ' + target, cwd=self.cwd)

    def test_start_upgrade(self):
        self.useBzrBranches(direct_database=True)
        branch, tree = self.create_branch_and_tree(format='pack-0.92')
        last_revision = tree.commit('foo')
        with person_logged_in(branch.owner):
            branch_changed(branch, tree.branch)
        target = self.makeTemporaryDirectory()
        stdout, stderr, retcode = self.upgrade_all_branches(target)
        self.assertEqual('', stderr)
        self.assertEqual(0, retcode)
