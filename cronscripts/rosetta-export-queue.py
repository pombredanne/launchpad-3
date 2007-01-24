#!/usr/bin/python
# Copyright 2005 Canonical Ltd. All rights reserved.

import _pythonpath

import logging
import sys
from optparse import OptionParser

from contrib.glock import GlobalLock, LockAlreadyAcquired

from canonical.lp import initZopeless, READ_COMMITTED_ISOLATION
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, logger as logger_from_options)
from canonical.launchpad.scripts.po_export_queue import process_queue

def main(args):
    parser = OptionParser()
    logger_options(parser, logging.WARNING)
    options, args = parser.parse_args()
    logger = logger_from_options(options)

    lockfile_path = '/var/lock/rosetta-export-queue.lock'
    lockfile = GlobalLock(lockfile_path, logger=logger)

    try:
        lockfile.acquire()
    except LockAlreadyAcquired:
        logger.error('Lockfile %s already exists, exiting.' % lockfile_path)
        return 0

    try:
        ztm = initZopeless(
            dbuser='poexport', isolation=READ_COMMITTED_ISOLATION)
        execute_zcml_for_scripts()
        process_queue(ztm, logger)
        logger.info('Done.')
        return 0
    finally:
        lockfile.release()

if __name__ == '__main__':
    sys.exit(main(sys.argv))

