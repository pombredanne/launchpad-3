__metaclass__ = type

import logging

from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir, format_registry
from bzrlib.plugins.loom.branch import loomify
from bzrlib.repository import Repository
from bzrlib.revision import NULL_REVISION
from testtools.testcase import ExpectedException
from zope.security.proxy import removeSecurityProxy

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

    def prepare(self, format='pack-0.92', loomify_branch=False):
        self.useBzrBranches(direct_database=True)
        branch, tree = self.create_branch_and_tree(format=format)
        tree.commit('foo', rev_id='prepare-commit')
        if loomify_branch:
            loomify(tree.branch)
            bzr_branch = Branch.open(tree.branch.base)
        else:
            bzr_branch = tree.branch
        return self.getUpgrader(bzr_branch, branch)

    def getUpgrader(self, bzr_branch, branch=None):
        target_dir = self.useContext(temp_dir())
        return Upgrader(
            branch, target_dir, logging.getLogger(), bzr_branch)

    def addTreeReference(self, tree):
        sub_branch = BzrDir.create_branch_convenience(
            tree.bzrdir.root_transport.clone('sub').base)
        tree.add_reference(sub_branch.bzrdir.open_workingtree())
        tree.commit('added tree reference')

    def upgrade_by_fetch(self, bzr_branch, target_dir):
        """Run Upgrader.upgrade_by_fetch on a branch."""
        bzr_branch = removeSecurityProxy(bzr_branch)
        with read_locked(bzr_branch):
            Upgrader(None, None, logging.getLogger(),
                bzr_branch=bzr_branch).upgrade_by_fetch(target_dir)
        return Branch.open(target_dir)

    def check_branch(self, upgraded, branch_format=BranchFormat.BZR_BRANCH_7):
        """Check that a branch matches expected post-upgrade formats."""
        control, branch, repository = get_branch_formats(upgraded)
        self.assertEqual(repository, RepositoryFormat.BZR_CHK_2A)
        self.assertEqual(branch, branch_format)

    def test_simple_upgrade(self):
        """Upgrade a pack-0.92 branch."""
        upgrader = self.prepare()
        upgraded = Branch.open(upgrader.upgrade())
        self.check_branch(upgraded)

    def test_subtree_upgrade(self):
        """Upgrade a pack-0.92-subtree branch."""
        upgrader = self.prepare('pack-0.92-subtree')
        upgraded = Branch.open(upgrader.upgrade())
        self.check_branch(upgraded)

    def test_upgrade_loom(self):
        """Upgrade a loomified pack-0.92 branch."""
        upgrader = self.prepare(loomify_branch=True)
        upgraded = Branch.open(upgrader.upgrade())
        self.check_branch(upgraded, BranchFormat.BZR_LOOM_2)

    def test_upgrade_subtree_loom(self):
        """Upgrade a loomified pack-0.92-subtree branch."""
        upgrader = self.prepare('pack-0.92-subtree', loomify_branch=True)
        upgraded = Branch.open(upgrader.upgrade())
        self.check_branch(upgraded, BranchFormat.BZR_LOOM_2)

    def test_add_upgraded_branch_preserves_tip(self):
        """Fetch-based upgrade preserves branch tip."""
        upgrader = self.prepare('pack-0.92-subtree')
        upgrade_dir = self.useContext(temp_dir())
        with read_locked(upgrader.bzr_branch):
            upgrader.upgrade_by_fetch(upgrade_dir)
        upgraded = Branch.open(upgrade_dir)
        self.assertEqual('prepare-commit', upgraded.last_revision())
        self.assertEqual(
            'foo', upgraded.repository.get_revision('prepare-commit').message)

    def test_create_upgraded_repository_preserves_dead_heads(self):
        """Fetch-based upgrade preserves heads in the repository."""
        upgrader = self.prepare('pack-0.92-subtree')
        upgrader.bzr_branch.set_last_revision_info(0, NULL_REVISION)
        upgrade_dir = self.useContext(temp_dir())
        with read_locked(upgrader.bzr_branch):
            upgrader.create_upgraded_repository(upgrade_dir)
        upgraded = Repository.open(upgrade_dir)
        self.assertEqual(
            'foo', upgraded.get_revision('prepare-commit').message)

    def test_upgrade_by_fetch_preserves_tags(self):
        """Fetch-based upgrade preserves heads in the repository."""
        upgrader = self.prepare('pack-0.92-subtree')
        upgrader.bzr_branch.tags.set_tag('steve', 'rev-id')
        upgrade_dir = self.useContext(temp_dir())
        with read_locked(upgrader.bzr_branch):
            upgrader.upgrade_by_fetch(upgrade_dir)
        upgraded = Branch.open(upgrade_dir)
        self.assertEqual('rev-id', upgraded.tags.lookup_tag('steve'))

    def test_has_tree_references(self):
        """Detects whether repo contains actual tree references."""
        self.useBzrBranches(direct_database=True)
        format = format_registry.make_bzrdir('pack-0.92-subtree')
        branch, tree = self.create_branch_and_tree(format=format)
        upgrader = self.getUpgrader(tree.branch, branch)
        with read_locked(tree.branch.repository):
            self.assertFalse(upgrader.has_tree_references())
        self.addTreeReference(tree)
        with read_locked(tree.branch.repository):
            self.assertTrue(upgrader.has_tree_references())

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
            self.upgrade_by_fetch(tree.branch, target_dir)
