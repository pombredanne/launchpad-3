#!/usr/bin/env python
# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Cronscript to prune old and unreferenced OOPS reports from the archive."""

__metaclass__ = type

import _pythonpath
from optparse import OptionParser
import os
import sys

from canonical.config import config
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.launchpad.scripts.logger import logger_options, logger
from canonical.launchpad.scripts.oops import (
        unwanted_oops_files, prune_empty_oops_directories
        )
from canonical.lp import initZopeless, AUTOCOMMIT_ISOLATION

default_lock_filename = '/var/lock/oops-prune.lock'

def main():
    parser = OptionParser("Usage: %prog [OOPS_DIR ...]")
    parser.add_option(
            '-n', '--dry-run', default=False, action='store_true',
            dest="dry_run", help="Do a test run. No files are removed."
            )
    logger_options(parser)
    options, args = parser.parse_args()

    # Default to using the OOPS directory in config file.
    if not args:
        args = [config.launchpad.errorreports.errordir]

    oops_directories = []
    for oops_dir in args:
        if not os.path.isdir(oops_dir):
            parser.error("%s is not a directory" % oops_dir)

        oops_directories.append(oops_dir)

    log = logger(options, 'oops-prune')

    # Create a lock file so we don't have two daemons running at the same time.
    lockfile = LockFile(default_lock_filename, logger=log)
    try:
        lockfile.acquire()
    except OSError:
        log.info("lockfile %s already exists, exiting", default_lock_filename)
        return 1

    try:
        ztm = initZopeless(dbuser='oopsprune', isolation=AUTOCOMMIT_ISOLATION)
        for oops_directory in oops_directories:
            for oops_path in unwanted_oops_files(oops_directory, 90, log):
                log.info("Removing %s", oops_path)
                if not options.dry_run:
                    os.unlink(oops_path)

        prune_empty_oops_directories(oops_directory)

        return 0
    finally:
        lockfile.release()


if __name__ == '__main__':
    sys.exit(main())
