#!/usr/bin/python -S

__metaclass__ = type

import _pythonpath

import sys
from lp.codehosting.upgrade import Upgrader
from lp.codehosting.bzrutils import server
from lp.codehosting.vfs.branchfs import get_rw_server
from lp.services.scripts.base import LaunchpadScript, LaunchpadScriptFailure


class UpgradeAllBranches(LaunchpadScript):

    def main(self):
        if len(self.args) < 1:
            raise LaunchpadScriptFailure('Please specify a target directory.')
        if len(self.args) > 1:
            raise LaunchpadScriptFailure('Too many arguments.')
        target_dir = self.args[0]
        with server(get_rw_server()):
            Upgrader.run_start_upgrade(target_dir, self.logger)


if __name__ == "__main__":
    sys.stderr.write(repr(sys.argv))
    script = UpgradeAllBranches(
        "upgrade-all-branches", dbuser='upgrade-branches')
    script.lock_and_run()
