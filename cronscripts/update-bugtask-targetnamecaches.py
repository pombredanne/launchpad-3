#!/usr/bin/env python
# Copyright 2005 Canonical Ltd.  All rights reserved.

# This script updates the cached stats in the system

import _pythonpath

import sys

from optparse import OptionParser

from zope.component import getUtility

from canonical.lp import initZopeless
from canonical.launchpad.interfaces import IBugTaskSet
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, logger)
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.config import config

_default_lock_file = '/var/lock/launchpad-targetnamecacheupdater.lock'

def update_bugtask_targetname_caches():
    """Update the targetnamecache for all IBugTasks.

    This ensures that the cache values are up-to-date even after, for example,
    an IDistribution being renamed.
    """
    ztm = initZopeless(dbuser=config.targetnamecacheupdater.dbuser,
                       implicitBegin=False)
    bugtaskset = getUtility(IBugTaskSet)
    ztm.begin()
    bugtask_ids = [bugtask.id for bugtask in bugtaskset]
    ztm.commit()
    for bugtask_id in bugtask_ids:
        ztm.begin()
        bugtask = bugtaskset.get(bugtask_id)
        bugtask.updateTargetNameCache()
        ztm.commit()


if __name__ == '__main__':
    parser = OptionParser()
    logger_options(parser)
    (options, arguments) = parser.parse_args()
    if arguments:
        parser.error("Unhandled arguments %s" % repr(arguments))
    execute_zcml_for_scripts()

    log = logger(options, 'update-bugtask-targetnamecaches')
    log.info("Updating targetname cache of bugtasks.")

    lockfile = LockFile(_default_lock_file, logger=log)
    try:
        lockfile.acquire()
    except OSError:
        log.info("lockfile %s already exists, exiting", _default_lock_file)
        sys.exit(1)

    try:
        update_bugtask_targetname_caches()
    finally:
        lockfile.release()

    log.info("Finished updating targetname cache of bugtasks.")

    sys.exit(0)
