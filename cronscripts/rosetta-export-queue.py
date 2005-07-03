#!/usr/bin/python
# Copyright 2005 Canonical Ltd. All rights reserved.

import logging
import sys
from optparse import OptionParser

from canonical.lp import initZopeless
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, logger as logger_from_options)
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.launchpad.scripts.po_export_queue import process_queue

def main(args):
    parser = OptionParser()
    logger_options(parser, logging.WARNING)
    options, args = parser.parse_args()
    logger = logger_from_options(options)

    lockfile_path = '/var/lock/rosetta-export-queue.lock'
    lockfile = LockFile(lockfile_path)

    try:
        lockfile.acquire()
    except OSError:
        logger.info('Lockfile %s already exists, exiting.' % lockfile_path)
        return 0

    try:
        ztm = initZopeless()
        execute_zcml_for_scripts()
        process_queue(ztm, logger)
    except:
        logger.exception('Uncaught exception while processing the queue.')
        lockfile.release()
        return 1

    logger.info('Done.')
    lockfile.release()
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

