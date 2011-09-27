__metaclass__ = type

import logging

from bzrlib.branch import Branch
from bzrlib.revision import NULL_REVISION

from canonical.testing.layers import ZopelessDatabaseLayer
from lp.code.bzr import (
    BranchFormat,
    get_branch_formats,
    RepositoryFormat,
    )
from lp.codehosting.upgrade import Upgrader
from lp.testing import (
    temp_dir,
    TestCaseWithFactory,
    )


class TestUpgrader(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def prepare(self, format='knit'):
        self.useBzrBranches(direct_database=True)
        branch, tree = self.create_branch_and_tree(format=format)
        tree.commit('foo', rev_id='prepare-commit')
        target_dir = self.useContext(temp_dir())
        return branch, target_dir

    def upgrade(self, target_dir, branch):
        return Upgrader(target_dir, logging.getLogger()).upgrade(branch)

    def upgrade_by_pull(self, bzr_branch, target_dir):
        Upgrader(None, logging.getLogger()).upgrade_by_pull(
            bzr_branch, target_dir)
        return Branch.open(target_dir)

    def check_branch(self, upgraded):
        control, branch, repository = get_branch_formats(upgraded)
        self.assertEqual(repository, RepositoryFormat.BZR_CHK_2A)
        self.assertEqual(branch, BranchFormat.BZR_BRANCH_7)

    def test_simple_upgrade(self):
        branch, target_dir = self.prepare()
        upgraded = Branch.open(self.upgrade(target_dir, branch))
        self.check_branch(upgraded)

    def test_subtree_upgrade(self):
        branch, target_dir = self.prepare('pack-0.92-subtree')
        upgraded = Branch.open(self.upgrade(target_dir, branch))
        self.check_branch(upgraded)

    def test_upgrade_by_pull_preserves_tip(self):
        branch, target_dir = self.prepare('pack-0.92-subtree')
        bzr_branch = branch.getBzrBranch()
        upgraded = self.upgrade_by_pull(bzr_branch, target_dir)
        self.assertEqual('prepare-commit', upgraded.last_revision())
        self.assertEqual(
            'foo', upgraded.repository.get_revision('prepare-commit').message)

    def test_upgrade_by_pull_preserves_dead_heads(self):
        branch, target_dir = self.prepare('pack-0.92-subtree')
        bzr_branch = branch.getBzrBranch()
        bzr_branch.set_last_revision_info(0, NULL_REVISION)
        upgraded = self.upgrade_by_pull(bzr_branch, target_dir)
        self.assertEqual(NULL_REVISION, upgraded.last_revision())
        self.assertEqual(
            'foo', upgraded.repository.get_revision('prepare-commit').message)

    def test_upgrade_by_pull_preserves_tags(self):
        branch, target_dir = self.prepare('pack-0.92-subtree')
        bzr_branch = branch.getBzrBranch()
        bzr_branch.tags.set_tag('steve', 'rev-id')
        upgraded = self.upgrade_by_pull(bzr_branch, target_dir)
        self.assertEqual('rev-id', upgraded.tags.lookup_tag('steve'))
