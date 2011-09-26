#!/usr/bin/python -S

__metaclass__ = type

import _pythonpath

from lp.codehosting.upgrade import Upgrader
from canonical.launchpad.interfaces.lpstorm import IStore
from lp.code.bzr import RepositoryFormat
from lp.code.model.branch import Branch
from lp.services.scripts.base import LaunchpadScript, LaunchpadScriptFailure


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
        Upgrader.run(branches, target_dir, self.logger)


if __name__ == "__main__":
    script = UpgradeAllBranches(
        "upgrade-all-branches", dbuser='upgrade-branches')
    script.lock_and_run()
