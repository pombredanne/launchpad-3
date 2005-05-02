#!/usr/bin/env python
# Copyright 2005 Canonical Ltd.  All rights reserved.

import logging
import sys
from optparse import OptionParser

from canonical.lp import initZopeless
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.launchpad.scripts.rosetta import AttachTranslationCatalog, \
    fetch_date_list, fetch_catalog

_default_lock_file = '/var/lock/rosetta-package-po-attach.lock'

def parse_options():
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

    (options, args) = parser.parse_args()

    return options

def setup_logger(logger):
    loglevel = logging.WARN

    for i in range(options.verbose):
        if loglevel == logging.INFO:
            loglevel = logging.DEBUG
        elif loglevel == logging.WARN:
            loglevel = logging.INFO

    for i in range(options.quiet):
        if loglevel == logging.WARN:
            loglevel = logging.ERROR
        elif loglevel == logging.ERROR:
            loglevel = logging.CRITICAL

    hdlr = logging.StreamHandler(strm=sys.stderr)
    hdlr.setFormatter(
        logging.Formatter(fmt='%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(hdlr)
    logger.setLevel(loglevel)

def main(archive_uri, ztm, logger):
    dates_list = fetch_date_list(archive_uri, logger)

    for date in dates_list:
        catalog = fetch_catalog(archive_uri, date, logger)
        process = AttachTranslationCatalog(
            archive_uri + '/' + date, catalog, ztm, logger)
        process.run()

if __name__ == '__main__':
    options = parse_options()

    # Get the global logger for this task.
    logger = logging.getLogger("rosetta-package-po-attach")
    # Customize the logger output.
    setup_logger(logger)

    # Create a lock file so we don't have two daemons running at the same time.
    lockfile = LockFile(options.lockfilename, logger=logger)
    try:
        lockfile.acquire()
    except OSError:
        logger.info("lockfile %s already exists, exiting",
                    options.lockfilename)
        sys.exit(0)

    ztm = initZopeless()

    # Bare except clause: so that the lockfile is reliably deleted.

    try:
        main(options.archive_uri, ztm, logger)
    except:
        # Release the lock for the next invocation.
        logger.error('An unexpected exception ocurred', exc_info = 1)
        lockfile.release()
        sys.exit(1)

    # Release the lock for the next invocation.
    lockfile.release()
    sys.exit(0)

