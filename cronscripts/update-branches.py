#!/usr/bin/env python
# Copyright 2005 Canonical Ltd.  All rights reserved.
# Author: Gustavo Niemeyer <gustavo@niemeyer.net>

"""Update bzr branches information in the database"""


import _pythonpath

import sys
import logging
from optparse import OptionParser

from bzrlib.errors import NotBranchError, ConnectionError

from zope.component import getUtility
from canonical.lp import initZopeless
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, logger, log)
from canonical.launchpad.interfaces import IBranchSet
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.config import config

from importd.bzrsync import BzrSync


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
    lockfile = LockFile(options.lockfilename, logger=log)
    try:
        lockfile.acquire()
    except OSError:
        log.info("lockfile %s already exists, exiting", options.lockfilename)
        return 1

    # We don't want debug messages from bzr at that point.
    bzr_logger = logging.getLogger("bzr")
    bzr_logger.setLevel(logging.INFO)

    try:
        # Setup zcml machinery to be able to use getUtility
        execute_zcml_for_scripts()
        ztm = initZopeless(dbuser=config.branchupdater.dbuser)

        log.debug('Starting branches update')
        branchset = getUtility(IBranchSet)
        for branch in branchset:
            try:
                sync_one_branch(ztm, branch)
            except (KeyboardInterrupt, SystemExit):
                # If either was raised, something really wants us to finish.
                # Any other Exception is an error condition and must not
                # terminate the script.
                raise
            except:
                # Yes, bare except. Bugs or error conditions when syncing any
                # given branch must not prevent syncing the other branches.
                log_scan_failure(branch)
                log.exception('Unhandled exception')
        log.debug('Finished branches update')
    finally:
        lockfile.release()

    return 0


def sync_one_branch(ztm, branch):
    """Run BzrSync on a single branch and handle expected exceptions."""
    try:
        bzrsync = BzrSync(
            ztm, branch.id, branch_warehouse_url(branch), log)
    except NotBranchError:
        # The branch is not present in the Warehouse
        log_scan_failure(branch, "Branch not found")
        return
    try:
        bzrsync.syncHistory()
    except ConnectionError:
        # A network glitch occured. Yes, that does happen.
        log.shortException("Transient network failure")
        log_scan_failure(branch)


def log_scan_failure(branch, message="Failed to scan"):
    """Log diagnostic information for branches that could not be scanned."""
    log.warning("%s: %s\n    branch.url = %r",
                message, branch_warehouse_url(branch), branch.url)


def branch_warehouse_url(branch):
    # the prefixurl in the config should normally end with '/'
    prefixurl = config.branchupdater.prefixurl        
    return "%s%08x" % (prefixurl, branch.id)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
