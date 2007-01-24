#!/usr/bin/env python
# Copyright 2005 Canonical Ltd.  All rights reserved.
# Author: Gustavo Niemeyer <gustavo@niemeyer.net>
#         David Allouche <david@allouche.net>

"""Update bzr branches information in the database"""


import _pythonpath

import sys
import logging
from optparse import OptionParser

from contrib.glock import GlobalLock, LockAlreadyAcquired

from canonical.lp import initZopeless
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, logger, log)
from canonical.config import config

from canonical.launchpad.scripts.branch_scanner import BranchScanner

default_lock_file = '/var/lock/launchpad-updatebranches.lock'


def parse_options(args):
    """Parse command line options"""

    parser = OptionParser()
    parser.add_option("-l", "--lockfile", dest="lockfilename",
        default=default_lock_file,
        help="The file the script should use to lock the process.")

    # Add the verbose/quiet options.
    logger_options(parser)

    (options, args) = parser.parse_args(args)
    return options


def main(argv):
    options = parse_options(argv[1:])

    # Get the global logger for this task.
    logger(options, 'update-branches')

    # Create a lock file so we don't have two daemons running at the same time.
    lockfile = GlobalLock(options.lockfilename, logger=log)
    try:
        lockfile.acquire()
    except LockAlreadyAcquired:
        log.error("lockfile %s already exists, exiting", options.lockfilename)
        return 1

    # We don't want debug messages from bzr at that point.
    bzr_logger = logging.getLogger("bzr")
    bzr_logger.setLevel(logging.INFO)

    try:
        # Setup zcml machinery to be able to use getUtility
        execute_zcml_for_scripts()
        ztm = initZopeless(dbuser=config.branchscanner.dbuser)

        # The actual work happens here
        BranchScanner(ztm, log).scanAllBranches()

    finally:
        lockfile.release()
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
