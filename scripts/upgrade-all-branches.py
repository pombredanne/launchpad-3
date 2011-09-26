#!/usr/bin/python -S

__metaclass__ = type

import _pythonpath

import os
from shutil import rmtree
from tempfile import mkdtemp

from bzrlib.bzrdir import BzrDir, format_registry
from bzrlib.transport import get_transport_from_path
from bzrlib.upgrade import upgrade

from canonical.launchpad.interfaces.lpstorm import IStore
from lp.code.bzr import RepositoryFormat
from lp.code.model.branch import Branch
from lp.codehosting.vfs import get_rw_server
from lp.services.scripts.base import (
    LaunchpadScript,
    LaunchpadScriptFailure,
    )

class AlreadyUpgraded(Exception):
    pass


class UpgradeAllBranches(LaunchpadScript):

    def main(self):
        if len(self.args) < 1:
            raise LaunchpadScriptFailure('Please specify a target directory.')
        if len(self.args) > 1:
            raise LaunchpadScriptFailure('Too many arguments.')
        target_dir = self.args[0]
        store = IStore(Branch)
        branches = store.find(
            Branch, Branch.repository_format != RepositoryFormat.BZR_CHK_2A)
        branches.order_by(Branch.unique_name)
        Upgrader.run(branches, target_dir)


class Upgrader:

    def __init__(self, target_dir):
        self.target_format = format_registry.make_bzrdir('2a')
        self.target_dir = target_dir

    @classmethod
    def run(cls, branches, target_dir):
        server = get_rw_server()
        server.start_server()
        try:
            cls(target_dir).upgrade_branches(branches)
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


if __name__ == "__main__":
    script = UpgradeAllBranches(
        "upgrade-all-branches", dbuser='upgrade-branches')
    script.lock_and_run()
