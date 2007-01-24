#!/usr/bin/env python
# Copyright 2004 Canonical Ltd.  All rights reserved.

# This script updates the cached stats in the system

import _pythonpath

import sys

from optparse import OptionParser

from zope.component import getUtility

from contrib.glock import GlobalLock, GlobalLockError

from canonical.lp import initZopeless, READ_COMMITTED_ISOLATION
from canonical.launchpad.interfaces import (
    IDistributionSet, ILaunchpadStatisticSet, IPersonSet
    )
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, logger)
from canonical.config import config

default_lock_file = '/var/lock/launchpad-stats.lock'

def parse_options(args):
    """Parse a set of command line options.

    Return an optparse.Values object.
    """
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
    logger_object = logger(options, 'launchpad-stats')

    # Create a lock file so we don't have two daemons running at the same time.
    lockfile = GlobalLock(options.lockfilename, logger=logger_object)
    try:
        lockfile.acquire()
    except GlobalLockError:
        logger_object.error("lockfile %s already exists, exiting",
                            options.lockfilename)
        return 1

    try:
        # Setup zcml machinery to be able to use getUtility
        execute_zcml_for_scripts()
        ztm = initZopeless(
                dbuser=config.statistician.dbuser,
                isolation=READ_COMMITTED_ISOLATION
                )

        # Do the stats update
        logger_object.debug('Starting the stats update')
        distroset = getUtility(IDistributionSet)
        for distro in distroset:
            for distrorelease in distro.releases:
                distrorelease.updateStatistics(ztm)
        launchpad_stats = getUtility(ILaunchpadStatisticSet)
        launchpad_stats.updateStatistics(ztm)

        getUtility(IPersonSet).updateStatistics(ztm)

        #ztm.commit() Content objects are responsible for committing.
        logger_object.debug('Finished the stats update')
        return 0
    finally:
        lockfile.release()

if __name__ == '__main__':
    sys.exit(main(sys.argv))

