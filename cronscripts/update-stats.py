#!/usr/bin/env python
# Copyright 2004 Canonical Ltd.  All rights reserved.

# This script updates the cached stats in the system

import _pythonpath

import sys

from optparse import OptionParser

from zope.component import getUtility

from canonical.lp import initZopeless
from canonical.launchpad.interfaces import (
    IDistributionSet, IRosettaApplication)
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, logger)
from canonical.launchpad.scripts.lockfile import LockFile
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
    lockfile = LockFile(options.lockfilename, logger=logger_object)
    try:
        lockfile.acquire()
    except OSError:
        logger_object.info("lockfile %s already exists, exiting",
                           options.lockfilename)
        return 1

    try:
        # Setup zcml machinery to be able to use getUtility
        execute_zcml_for_scripts()
        ztm = initZopeless(dbuser=config.statistician.dbuser)

        # Do the stats update
        logger_object.debug('Starting the stats update')
        distroset = getUtility(IDistributionSet)
        for distro in distroset:
            for distrorelease in distro.releases:
                distrorelease.updateStatistics()
        rosetta_app = getUtility(IRosettaApplication)
        rosetta_app.updateStatistics()
        ztm.commit()
        logger_object.debug('Finished the stats update')
        return 0
    finally:
        lockfile.release()

if __name__ == '__main__':
    sys.exit(main(sys.argv))

