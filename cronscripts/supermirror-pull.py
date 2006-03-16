#!/usr/bin/env python
# Copyright 2006 Canonical Ltd.  All rights reserved.

import sys

import _pythonpath

from optparse import OptionParser

from zope.component import getUtility

from canonical.launchpad.scripts.supermirror import mirror
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, logger)
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.launchpad.interfaces import IBranchSet

_default_lock_file = '/var/lock/launchpad-karma-update.lock'

if __name__ == '__main__':
    parser = OptionParser()
    logger_options(parser)
    (options, arguments) = parser.parse_args()
    if arguments:
        parser.error("Unhandled arguments %s" % repr(arguments))
    execute_zcml_for_scripts()

    log = logger(options, 'karmacache')
    log.info("Pulling branches for the supermirror.")

    lockfile = LockFile(_default_lock_file, logger=log)
    try:
        lockfile.acquire()
    except OSError:
        log.info("lockfile %s already exists, exiting", _default_lock_file)
        sys.exit(1)

    branches = getUtility(IBranchSet).get_supermirror_pull_queue()
    try:
        mirror(branches)
    finally:
        lockfile.release()

    log.info("Finished pulling branches for the supermirror.")

