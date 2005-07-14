#!/usr/bin/env python
# Copyright 2004 Canonical Ltd.  All rights reserved.

import _pythonpath

import sys

from optparse import OptionParser

from canonical.lp import initZopeless
from canonical.launchpad.scripts import (execute_zcml_for_scripts,
    logger_options, logger)
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.launchpad.scripts.rosetta import ImportProcess

default_lock_file = '/var/lock/launchpad-poimport.lock'

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
    logger_object = logger(options, 'rosetta-poimport')

    # Create a lock file so we don't have two daemons running at the same time.
    lockfile = LockFile(options.lockfilename, logger=logger_object)
    try:
        lockfile.acquire()
    except OSError:
        logger_object.info("lockfile %s already exists, exiting",
                           options.lockfilename)
        return 0

    try:
        # Setup zcml machinery to be able to use getUtility
        execute_zcml_for_scripts()
        ztm = initZopeless()

        # Do the import of all pending files from the queue.
        process = ImportProcess(ztm, logger_object)
        logger_object.debug('Starting the import process')
        process.run()
        logger_object.debug('Finished the import process')
        return 0
    finally:
        lockfile.release()


if __name__ == '__main__':
    sys.exit(main(sys.argv))
