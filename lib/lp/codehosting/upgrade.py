__metaclass__ = type

__all__ = ['Upgrader']

import os
from shutil import rmtree
from tempfile import mkdtemp

from bzrlib.bzrdir import BzrDir, format_registry
from bzrlib.errors import UpToDateFormat
from bzrlib.plugins.loom.formats import (
    NotALoom,
    require_loom_branch,
    )
from bzrlib.repofmt.groupcompress_repo import RepositoryFormat2aSubtree
from bzrlib.upgrade import upgrade
from zope.security.proxy import removeSecurityProxy

from lp.codehosting.bzrutils import read_locked
from lp.codehosting.vfs.branchfs import (
    get_real_branch_path,
    get_rw_server,
    )


class AlreadyUpgraded(Exception):
    pass


class Upgrader:
    """Upgrades branches to 2a-based formats if possible."""

    def __init__(self, branch, target_dir, logger, bzr_branch=None):
        self.branch = branch
        self.bzr_branch = bzr_branch
        if self.bzr_branch is None:
            self.bzr_branch = removeSecurityProxy(self.branch.getBzrBranch())
        self.target_dir = target_dir
        self.target_subdir = os.path.join(self.target_dir, str(self.branch.id))
        self.logger = logger

    def get_bzrdir(self):
        """Return the target_subdir bzrdir."""
        return BzrDir.open(self.target_subdir)

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
        if getattr(
            self.bzr_branch.repository._format, 'supports_tree_reference',
            False):
            if self.has_tree_references():
                format._repository_format = RepositoryFormat2aSubtree()
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
                    skipped += 1
            logger.info('Skipped %d already-upgraded branches.', skipped)
        finally:
            server.stop_server()

    def finish_upgrade(self):
        """Create an upgraded version of self.branch in self.target_dir."""
        self.logger.info(
            'Upgrading branch %s (%s)', self.branch.unique_name,
            self.branch.id)
        with read_locked(self.bzr_branch):
            bd = self.add_upgraded_branch()
        self.swap_in()

    def add_upgraded_branch(self):
        """Add an upgraded branch to the target_subdir.

        self.branch's branch (but not repository) is mirrored to the BzrDir
        and then the bzrdir is upgraded in the normal way.
        """
        bd = self.get_bzrdir()
        self.mirror_branch(self.bzr_branch, bd)
        try:
            exceptions = upgrade(
                bd.root_transport.base, self.get_target_format())
            if exceptions:
                if len(exceptions) == 1:
                    # Compatibility with historical behavior
                    raise exceptions[0]
                else:
                    return 3
        except UpToDateFormat:
            pass
        return bd

    def start_upgrade(self):
        if os.path.exists(self.target_subdir):
            raise AlreadyUpgraded
        with read_locked(self.bzr_branch):
            self.create_upgraded_repository()

    def create_upgraded_repository(self):
        """Create a repository in an upgraded format.

        :param upgrade_dir: The directory to create the repository in.
        :return: The created repository.
        """
        self.logger.info('Converting repository with fetch.')
        upgrade_dir = mkdtemp(dir=self.target_dir)
        try:
            bzrdir = BzrDir.create(upgrade_dir, self.get_target_format())
            repository = bzrdir.create_repository()
            repository.fetch(self.bzr_branch.repository)
        except:
            rmtree(upgrade_dir)
            raise
        else:
            os.rename(upgrade_dir, self.target_subdir)

    def swap_in(self):
        """Swap the upgraded branch into place."""
        real_location = get_real_branch_path(self.branch.id)
        backup_dir = os.path.join(self.target_subdir, 'backup.bzr')
        os.rename(real_location, backup_dir)
        os.rename(self.target_subdir, real_location)

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
