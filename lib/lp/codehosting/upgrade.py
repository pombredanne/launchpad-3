__metaclass__ = type

__all__ = ['Upgrader']

import os
from shutil import rmtree
from tempfile import mkdtemp

from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir, format_registry
from bzrlib.errors import UpToDateFormat
from bzrlib.plugins.loom.formats import (
    NotALoom,
    require_loom_branch,
    )
from bzrlib.transport import get_transport_from_path
from bzrlib.upgrade import upgrade
from zope.security.proxy import removeSecurityProxy

from lp.codehosting.bzrutils import read_locked
from lp.codehosting.vfs import get_rw_server


class AlreadyUpgraded(Exception):
    pass


class HasTreeReferences(Exception):
    pass


class Upgrader:
    """Upgrades branches to 2a-based formats if possible."""

    def __init__(self, branch, target_dir, logger, bzr_branch=None):
        self.branch = branch
        self.bzr_branch = bzr_branch
        if self.bzr_branch is None:
            self.bzr_branch = removeSecurityProxy(self.branch.getBzrBranch())
        self.target_dir = target_dir
        self.logger = logger

    @property
    def target_subdir(self):
        return os.path.join(self.target_dir, str(self.branch.id))

    def get_target_format(self):
        """Return the format to upgrade a branch to.

        The repository format is always upgraded to a 2a format, but
        the branch format is left alone if the branch is a loom.
        :param branch: The bzr branch to upgrade
        :return: A Metadir format instance.
        """
        format = format_registry.make_bzrdir('2a')
        try:
            require_loom_branch(self.bzr_branch)
        except NotALoom:
            pass
        else:
            format._branch_format = self.bzr_branch._format
        return format

    @classmethod
    def run(cls, branches, target_dir, logger):
        """Upgrade listed branches to a target directory.

        :param branches: The Launchpad Branches to upgrade.
        :param target_dir: The directory to store upgraded versions in.
        """
        server = get_rw_server()
        server.start_server()
        try:
            skipped = 0
            for branch in branches:
                upgrader = cls(branch, target_dir, logger)
                try:
                    upgrader.upgrade(branch)
                except AlreadyUpgraded:
                    skipped +=1
            logger.info('Skipped %d already-upgraded branches.', skipped)
        finally:
            server.stop_server()

    def upgrade(self):
        """Upgrade the specified branch any way possible.

        :param branch: The branch to upgrade.
        """
        if os.path.exists(self.target_subdir):
            raise AlreadyUpgraded
        self.logger.info(
            'Upgrading branch %s (%s)', self.branch.unique_name,
            self.branch.id)
        with read_locked(self.bzr_branch):
            upgrade_dir = mkdtemp(dir=self.target_dir)
            try:
                self.upgrade_by_fetch(upgrade_dir)
            except:
                rmtree(upgrade_dir)
                raise
            else:
                os.rename(upgrade_dir, self.target_subdir)
                return self.target_subdir

    def upgrade_at_transport(self, transport):
        """Upgrade the branch at a specified transport in the standard way.

        The upgrade is performed through the normal Bazaar machinery.
        :param transport: A transport that is the base of the branch.
        """
        branch = Branch.open_from_transport(transport)
        self.logger.info('Performing standard upgrade.')
        exceptions = upgrade(branch.base, self.get_target_format())
        if exceptions:
            if len(exceptions) == 1:
                # Compatibility with historical behavior
                raise exceptions[0]
            else:
                return 3

    def upgrade_by_fetch(self, upgrade_dir):
        """Create an upgraded version of a specified branch.

        The upgrade is achieved by creating a new repository, fetching the
        branch's repository into it, copying the branch into it, and finally
        upgrading the entire branch using the normal Bazaar mechanism.

        :param bzr_branch: The branch to upgrade.
        :param upgrade_dir: The directory to upgrade to.
        """
        self.logger.info('Checking for tree-references.')
        if self.has_tree_references():
            raise HasTreeReferences
        self.logger.info('Converting repository with fetch.')
        branch = BzrDir.create_branch_convenience(
            upgrade_dir, force_new_tree=False)
        branch.repository.fetch(self.bzr_branch.repository)
        bd = branch.bzrdir
        bd.destroy_branch()
        self.mirror_branch(self.bzr_branch, bd)
        try:
            self.upgrade_at_transport(bd.root_transport)
        except UpToDateFormat:
            pass

    def has_tree_references(self):
        """Determine whether a repository contains tree references.

        :return: True if it contains tree references, False otherwise.
        """
        repo = self.bzr_branch.repository
        revision_ids = repo.all_revision_ids()
        for tree in repo.revision_trees(revision_ids):
            for path, entry in tree.iter_entries_by_dir():
                if entry.kind == 'tree-reference':
                    return True
        return False

    def mirror_branch(self, bzr_branch, target_bd):
        """Mirror the actual branch from a bzr_branch to a target bzrdir."""
        target = target_bd.get_branch_transport(bzr_branch._format)
        source = bzr_branch.bzrdir.get_branch_transport(bzr_branch._format)
        source.copy_tree_to_transport(target)
