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

    def __init__(self, target_dir, logger):
        self.target_dir = target_dir
        self.logger = logger

    def get_target_format(self, branch):
        format = format_registry.make_bzrdir('2a')
        try:
            require_loom_branch(branch)
        except NotALoom:
            pass
        else:
            format._branch_format = branch._format
        return format

    @classmethod
    def run(cls, branches, target_dir, logger):
        server = get_rw_server()
        server.start_server()
        try:
            cls(target_dir, logger).upgrade_branches(branches)
        finally:
            server.stop_server()

    def upgrade_branches(self, branches):
        skipped = 0
        for branch in branches:
            try:
                self.upgrade(branch)
            except AlreadyUpgraded:
                skipped +=1
        self.logger.info('Skipped %d already-upgraded branches.', skipped)

    def upgrade(self, branch):
        temp_location = os.path.join(self.target_dir, str(branch.id))
        if os.path.exists(temp_location):
            raise AlreadyUpgraded
        self.logger.info(
            'Upgrading branch %s (%s)', branch.unique_name, branch.id)
        bzr_branch = removeSecurityProxy(branch.getBzrBranch())
        with read_locked(bzr_branch):
            upgrade_dir = mkdtemp(dir=self.target_dir)
            try:
                if getattr(
                    bzr_branch.repository._format, 'supports_tree_reference',
                    False):
                    self.upgrade_by_pull(bzr_branch, upgrade_dir)
                else:
                    self.upgrade_to_dir(bzr_branch, upgrade_dir)
            except:
                rmtree(upgrade_dir)
                raise
            else:
                os.rename(upgrade_dir, temp_location)
                return temp_location

    def upgrade_dir(self, transport):
        branch = Branch.open_from_transport(transport)
        self.logger.info('Performing standard upgrade.')
        exceptions = upgrade(branch.base, self.get_target_format(branch))
        if exceptions:
            if len(exceptions) == 1:
                # Compatibility with historical behavior
                raise exceptions[0]
            else:
                return 3

    def upgrade_to_dir(self, bzr_branch, upgrade_dir):
        self.logger.info('Mirroring branch.')
        t = get_transport_from_path(upgrade_dir)
        bzr_branch.bzrdir.root_transport.copy_tree_to_transport(t)
        self.upgrade_dir(t)

    def upgrade_by_pull(self, bzr_branch, upgrade_dir):
        self.check_tree_references(bzr_branch.repository)
        self.logger.info('Converting repository with fetch.')
        branch = BzrDir.create_branch_convenience(
            upgrade_dir, force_new_tree=False)
        branch.repository.fetch(bzr_branch.repository)
        bd = branch.bzrdir
        bd.destroy_branch()
        self.mirror_branch(bzr_branch, bd)
        try:
            self.upgrade_dir(bd.root_transport)
        except UpToDateFormat:
            pass

    def check_tree_references(self, repo):
        self.logger.info('Checking for tree-references.')
        with read_locked(repo):
            revision_ids = repo.all_revision_ids()
            for tree in repo.revision_trees(revision_ids):
                for path, entry in tree.iter_entries_by_dir():
                    if entry.kind == 'tree-reference':
                        raise HasTreeReferences()

    def mirror_branch(self, bzr_branch, target_bd):
        target = target_bd.get_branch_transport(bzr_branch._format)
        source = bzr_branch.bzrdir.get_branch_transport(bzr_branch._format)
        source.copy_tree_to_transport(target)
