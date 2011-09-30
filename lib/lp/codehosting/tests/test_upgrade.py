__metaclass__ = type

import logging

from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir, format_registry
from bzrlib.plugins.loom.branch import loomify
from bzrlib.revision import NULL_REVISION
from testtools.testcase import ExpectedException

from canonical.testing.layers import ZopelessDatabaseLayer
from lp.code.bzr import (
    BranchFormat,
    get_branch_formats,
    RepositoryFormat,
    )
from lp.codehosting.bzrutils import read_locked
from lp.codehosting.upgrade import (
    HasTreeReferences,
    Upgrader,
    )
from lp.testing import (
    temp_dir,
    TestCaseWithFactory,
    )


class TestUpgrader(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def prepare(self, format='pack-0.92'):
        self.useBzrBranches(direct_database=True)
        branch, tree = self.create_branch_and_tree(format=format)
        tree.commit('foo', rev_id='prepare-commit')
        target_dir = self.useContext(temp_dir())
        return branch, target_dir

    def upgrade(self, target_dir, branch):
        """Run Upgrader.upgrade on a branch."""
        return Upgrader(target_dir, logging.getLogger()).upgrade(branch)

    def upgrade_by_fetch(self, bzr_branch, target_dir):
        """Run Upgrader.upgrade_by_fetch on a branch."""
        with read_locked(bzr_branch):
            Upgrader(None, logging.getLogger()).upgrade_by_fetch(
                bzr_branch, target_dir)
        return Branch.open(target_dir)

    def check_branch(self, upgraded, branch_format=BranchFormat.BZR_BRANCH_7):
        """Check that a branch matches expected post-upgrade formats."""
        control, branch, repository = get_branch_formats(upgraded)
        self.assertEqual(repository, RepositoryFormat.BZR_CHK_2A)
        self.assertEqual(branch, branch_format)

    def test_simple_upgrade(self):
        """Upgrade a pack-0.92 branch."""
        branch, target_dir = self.prepare()
        upgraded = Branch.open(self.upgrade(target_dir, branch))
        self.check_branch(upgraded)

    def test_subtree_upgrade(self):
        """Upgrade a pack-0.92-subtree branch."""
        branch, target_dir = self.prepare('pack-0.92-subtree')
        upgraded = Branch.open(self.upgrade(target_dir, branch))
        self.check_branch(upgraded)

    def test_upgrade_loom(self):
        """Upgrade a loomified pack-0.92 branch."""
        branch, target_dir = self.prepare()
        loomify(branch.getBzrBranch())
        upgraded = Branch.open(self.upgrade(target_dir, branch))
        self.check_branch(upgraded, BranchFormat.BZR_LOOM_2)

    def test_upgrade_subtree_loom(self):
        """Upgrade a loomified pack-0.92-subtree branch."""
        branch, target_dir = self.prepare('pack-0.92-subtree')
        loomify(branch.getBzrBranch())
        upgraded = Branch.open(self.upgrade(target_dir, branch))
        self.check_branch(upgraded, BranchFormat.BZR_LOOM_2)

    def test_upgrade_by_fetch_preserves_tip(self):
        """Fetch-based upgrade preserves branch tip."""
        branch, target_dir = self.prepare('pack-0.92-subtree')
        bzr_branch = branch.getBzrBranch()
        upgraded = self.upgrade_by_fetch(bzr_branch, target_dir)
        self.assertEqual('prepare-commit', upgraded.last_revision())
        self.assertEqual(
            'foo', upgraded.repository.get_revision('prepare-commit').message)

    def test_upgrade_by_fetch_preserves_dead_heads(self):
        """Fetch-based upgrade preserves heads in the repository."""
        branch, target_dir = self.prepare('pack-0.92-subtree')
        bzr_branch = branch.getBzrBranch()
        bzr_branch.set_last_revision_info(0, NULL_REVISION)
        upgraded = self.upgrade_by_fetch(bzr_branch, target_dir)
        self.assertEqual(NULL_REVISION, upgraded.last_revision())
        self.assertEqual(
            'foo', upgraded.repository.get_revision('prepare-commit').message)

    def test_upgrade_by_fetch_preserves_tags(self):
        """Fetch-based upgrade preserves heads in the repository."""
        branch, target_dir = self.prepare('pack-0.92-subtree')
        bzr_branch = branch.getBzrBranch()
        bzr_branch.tags.set_tag('steve', 'rev-id')
        upgraded = self.upgrade_by_fetch(bzr_branch, target_dir)
        self.assertEqual('rev-id', upgraded.tags.lookup_tag('steve'))

    def test_upgrade_by_fetch_dies_on_tree_references(self):
        """Subtree references prevent fetch-based upgrade."""
        self.useBzrBranches(direct_database=True)
        target_dir = self.useContext(temp_dir())
        format = format_registry.make_bzrdir('pack-0.92-subtree')
        branch, tree = self.create_branch_and_tree(format=format)
        sub_branch = BzrDir.create_branch_convenience(
            tree.bzrdir.root_transport.clone('sub').base, format=format)
        tree.add_reference(sub_branch.bzrdir.open_workingtree())
        tree.commit('added tree reference')
        with ExpectedException(HasTreeReferences):
            upgraded = self.upgrade_by_fetch(tree.branch, target_dir)
