#!/usr/bin/env python
# Copyright 2005 Canonical Ltd.  All rights reserved.
# Author: Gustavo Niemeyer <gustavo@niemeyer.net>

"""Update bzr branches information in the database"""


import _pythonpath

import sys
import traceback
import logging
from optparse import OptionParser

from bzrlib.errors import NotBranchError, ConnectionError

from zope.component import getUtility
from canonical.lp import initZopeless
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, logger)
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
    logger_object = logger(options, 'launchpad-updatebranches')

    # Create a lock file so we don't have two daemons running at the same time.
    lockfile = LockFile(options.lockfilename, logger=logger_object)
    try:
        lockfile.acquire()
    except OSError:
        logger_object.info("lockfile %s already exists, exiting",
                           options.lockfilename)
        return 1

    # We don't want debug messages from bzr at that point.
    bzr_logger = logging.getLogger("bzr")
    bzr_logger.setLevel(logging.INFO)

    try:
        # Setup zcml machinery to be able to use getUtility
        execute_zcml_for_scripts()
        ztm = initZopeless(dbuser=config.branchupdater.dbuser)

        logger_object.debug('Starting branches update')
        branchset = getUtility(IBranchSet)
        for branch in branchset:
            try:
                syncOneBranch(logger_object, ztm, branch)
            except (KeyboardInterrupt, SystemExit):
                # If either was raised, something really wants us to finish.
                # Any other Exception is an error condition and must not
                # terminate the script.
                raise
            except:
                # Yes, bare except. Bugs or error conditions when syncing any
                # given branch must not prevent syncing the other branches.
                logException(logger_object, with_traceback=True)
                logScanFailure(logger_object, branch)
        logger_object.debug('Finished branches update')
    finally:
        lockfile.release()

    return 0


def syncOneBranch(logger_object, ztm, branch):
    """Run BzrSync on a single branch and handle expected exceptions."""
    try:
        bzrsync = BzrSync(
            ztm, branch.id, branchWarehouseUrl(branch), logger_object)
    except NotBranchError:
        # The branch is not present in the Warehouse
        logScanFailure(logger_object, branch, "Branch not found")
        return
    try:
        bzrsync.syncHistory()
    except ConnectionError:
        # A network glitch occured. Yes, that does happen.
        logException(logger_object, with_traceback=False)
        logScanFailure(logger_object, branch)


def logException(logger_object, with_traceback):
    """Log the current exception at ERROR level with an optional traceback."""
    if with_traceback:
        report = traceback.format_exc()
    else:
        exctype, value = sys.exc_info()[:2]
        report = ''.join(traceback.format_exception_only(exctype, value))
    logger_object.error(report)


def logScanFailure(logger_object, branch, message="Failed to scan"):
    """Log diagnostic information for branches that could not be scanned."""
    logger_object.warning(
        "%s: %s", message, branchWarehouseUrl(branch))
    logger_object.warning("  branch.url = %r", branch.url)


def branchWarehouseUrl(branch):
    # the prefixurl in the config should normally end with '/'
    prefixurl = config.branchupdater.prefixurl        
    return "%s%08x" % (prefixurl, branch.id)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
