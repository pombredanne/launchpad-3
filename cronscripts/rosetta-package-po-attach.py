#!/usr/bin/env python
# Copyright 2005 Canonical Ltd.  All rights reserved.

import sys
from optparse import OptionParser

from canonical.lp import initZopeless
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.launchpad.scripts.rosetta import URLOpener, attach, \
    calculate_loglevel, create_logger
from canonical.launchpad.scripts import execute_zcml_for_scripts

_default_lock_file = '/var/lock/rosetta-package-po-attach.lock'

def parse_options(args):
    """Parse a set of command line options.

    Returns an optparse.Values object.
    """

    parser = OptionParser()
    parser.add_option("-v", "--verbose", dest="verbose",
        default=0, action="count",
        help="Displays extra information.")
    parser.add_option("-q", "--quiet", dest="quiet",
        default=0, action="count",
        help="Display less information.")
    parser.add_option("-l", "--lockfile", dest="lockfilename",
        default=_default_lock_file,
        help="The file the script should use to lock the process.")
    parser.add_option("-a", "--archive", dest="archive_uri",
        default="http://people.ubuntu.com/~lamont/translations/",
        help="The location of the archive from which to get translations")

    (options, args) = parser.parse_args(args)

    return options

def main(argv):
    options = parse_options(argv[1:])

    # Get the global logger for this task.
    loglevel = calculate_loglevel(options.quiet, options.verbose)
    logger = create_logger('rosetta-package-po-attach', loglevel)

    # Create a lock file so we don't have two daemons running at the same time.
    lockfile = LockFile(options.lockfilename, logger=logger)
    try:
        lockfile.acquire()
    except OSError:
        logger.info("lockfile %s already exists, exiting",
                    options.lockfilename)
        return 0

    execute_zcml_for_scripts()
    ztm = initZopeless()
    urlopener = URLOpener()

    # Bare except clause: so that the lockfile is reliably deleted.

    try:
        attach(urlopener, options.archive_uri, ztm, logger)
    except:
        # Release the lock for the next invocation.
        logger.error('An unexpected exception ocurred', exc_info = 1)
        lockfile.release()
        return 1

    # Release the lock for the next invocation.
    lockfile.release()
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

