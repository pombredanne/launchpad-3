#!/usr/bin/env python
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

import _pythonpath

import sys
from optparse import OptionParser
from contrib.glock import GlobalLock, LockAlreadyAcquired

from canonical.config import config
from canonical.lp import initZopeless
from canonical.launchpad.scripts import (execute_zcml_for_scripts, logger,
    logger_options)
from canonical.launchpad.scripts.rosetta import ImportProcess

default_lock = '/var/lock/launchpad-poimport.lock'

def parse_options(args):
    """Parse a set of command line options.

    Return an optparse.Values object.
    """
    parser = OptionParser()
    parser.add_option("-l", "--lockfile", dest="lockfile",
        default=default_lock,
        help="The lock file the script should use to lock the process.")

    # Add the verbose/quiet options.
    logger_options(parser)

    (options, args) = parser.parse_args(args)

    return options

def main(argv):
    options = parse_options(argv[1:])

    # Get the global logger for this task.
    logger_object = logger(options, 'rosetta-poimport')

    # Create a lock so we don't have two daemons running at the same time.
    lock = GlobalLock(options.lockfile)
    try:
        lock.acquire(blocking=False)
    except LockAlreadyAcquired:
        logger_object.info("lock %s already exists, exiting",
                           options.lockfile)
        return

    try:
        # Setup zcml machinery to be able to use getUtility
        execute_zcml_for_scripts()
        ztm = initZopeless(dbuser=config.rosetta.poimport.dbuser)

        # Do the import of all pending files from the queue.
        process = ImportProcess(ztm, logger_object)
        logger_object.debug('Starting the import process')
        process.run()
        logger_object.debug('Finished the import process')
    finally:
        # Release the lock for the next invocation.
        lock.release()

if __name__ == '__main__':
    main(sys.argv)
