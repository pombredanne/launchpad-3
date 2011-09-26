__metaclass__ = type

__all__ = ['Upgrader']

import os
from shutil import rmtree
from tempfile import mkdtemp

from bzrlib.bzrdir import BzrDir, format_registry
from bzrlib.transport import get_transport_from_path
from bzrlib.upgrade import upgrade

from lp.codehosting.vfs import get_rw_server


class AlreadyUpgraded(Exception):
    pass


class Upgrader:

    def __init__(self, target_dir, logger):
        self.target_format = format_registry.make_bzrdir('2a')
        self.target_dir = target_dir
        self.logger = logger

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
        bzr_branch = branch.getBzrBranch()
        upgrade_dir = mkdtemp(dir=self.target_dir)
        try:
            if getattr(bzr_branch.repository._format, 'supports_tree_reference',
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

    def upgrade_to_dir(self, bzr_branch, upgrade_dir):
        t = get_transport_from_path(upgrade_dir)
        bzr_branch.bzrdir.root_transport.copy_tree_to_transport(t)
        exceptions = upgrade(t.base, self.target_format)
        if exceptions:
            if len(exceptions) == 1:
                # Compatibility with historical behavior
                raise exceptions[0]
            else:
                return 3

    def upgrade_by_pull(self, bzr_branch, upgrade_dir):
        branch = BzrDir.create_branch_convenience(
            upgrade_dir, force_new_tree=False)
        branch.pull(bzr_branch)
