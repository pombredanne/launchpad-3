#!/usr/bin/python2.4
# Copyright 2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403
# Author: Gustavo Niemeyer <gustavo@niemeyer.net>
#         David Allouche <david@allouche.net>

"""Update bzr branches information in the database"""


import _pythonpath
import logging

from canonical.codehosting.scanner.branch_scanner import BranchScanner
from canonical.config import config
from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.webapp.errorlog import globalErrorUtility


class UpdateBranches(LaunchpadCronScript):
    def main(self):
        # We don't want debug messages from bzr at that point.
        bzr_logger = logging.getLogger("bzr")
        bzr_logger.setLevel(logging.INFO)
        globalErrorUtility.configure('branchscanner')

        BranchScanner(self.txn, self.logger).scanAllBranches()


if __name__ == '__main__':
    script = UpdateBranches(
        "updatebranches", dbuser=config.branchscanner.dbuser)
    script.lock_and_run()

