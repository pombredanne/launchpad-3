#!/usr/bin/env python
# Copyright 2005 Canonical Ltd.  All rights reserved.
# Author: Gustavo Niemeyer <gustavo@niemeyer.net>

"""Update bzr branches information in the database"""


import _pythonpath

import sys
import logging
from optparse import OptionParser

from bzrlib.errors import NotBranchError

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

        prefixurl = config.branchupdater.prefixurl

        branchset = getUtility(IBranchSet)

        for branch in branchset:
            branch_url = "%s/%d" % (prefixurl, branch.id)
            try:
                bzrsync = BzrSync(ztm, branch.id, branch_url, logger_object)
            except NotBranchError:
                logger_object.warning("Branch not found: %s" % branch_url)
            else: 
                bzrsync.syncHistory()

        logger_object.debug('Finished branches update')
    finally:
        lockfile.release()

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

