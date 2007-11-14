#!/usr/bin/python2.4
# Copyright 2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403
# Author: Gustavo Niemeyer <gustavo@niemeyer.net>
#         David Allouche <david@allouche.net>

"""Update bzr branches information in the database"""


import _pythonpath
import logging

from canonical.config import config
from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.codehosting.scanner.branch_scanner import BranchScanner


class UpdateBranches(LaunchpadCronScript):
    def main(self):
        # We don't want debug messages from bzr at that point.
        bzr_logger = logging.getLogger("bzr")
        bzr_logger.setLevel(logging.INFO)

        # Customize the oops reporting config
        oops_prefix = config.branchscanner.errorreports.oops_prefix
        config.launchpad.errorreports.oops_prefix = oops_prefix
        errordir = config.branchscanner.errorreports.errordir
        config.launchpad.errorreports.errordir = errordir
        copy_to_zlog = config.branchscanner.errorreports.copy_to_zlog
        config.launchpad.errorreports.copy_to_zlog = copy_to_zlog

        BranchScanner(self.txn, self.logger).scanAllBranches()


if __name__ == '__main__':
    script = UpdateBranches("updatebranches", dbuser=config.branchscanner.dbuser)
    script.lock_and_run()

