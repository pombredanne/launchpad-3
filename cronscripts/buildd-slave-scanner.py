#!/usr/bin/env python
# Copyright 2004 Canonical Ltd.  All rights reserved.
# Author: Daniel Silverstone <daniel.silverstone@canonical.com>
#         Celso Providelo <celso.providelo@canonical.com>
#
# Builder Slave Scanner and result collector

__metaclass__ = type

import _pythonpath

import sys
from optparse import OptionParser

from contrib.glock import GlobalLock, GlobalLockError

from zope.component import getUtility

from canonical.lp import initZopeless
from canonical.config import config
from canonical.buildmaster.master import BuilddMaster

from canonical.launchpad.interfaces import IDistroArchReleaseSet
from canonical.launchpad.scripts import (
        execute_zcml_for_scripts, logger_options, logger
        )

_default_lockfile = '/var/lock/buildd-master.lock'

def doSlaveScan(logger):
    """Proceed the Slave Scanning Process."""

    # setup a transaction manager
    tm = initZopeless(dbuser=config.builddmaster.dbuser)

    buildMaster = BuilddMaster(logger, tm)

    logger.info("Setting Builders.")

    # For every distroarchrelease we can find;
    # put it into the build master
    for archrelease in getUtility(IDistroArchReleaseSet):
        buildMaster.addDistroArchRelease(archrelease)
        buildMaster.setupBuilders(archrelease)

    logger.info("Scanning Builders.")
    # Scan all the pending builds; update logtails; retrieve
    # builds where they are compled
    result_code = buildMaster.scanActiveBuilders()

    # Now that the slaves are free, ask the buildmaster to calculate
    # the set of build candiates
    buildCandidatesSortedByProcessor = buildMaster.sortAndSplitByProcessor()

    logger.info("Dispatching Jobs.")
    # Now that we've gathered in all the builds;
    # dispatch the pending ones
    for processor, buildCandidates in \
            buildCandidatesSortedByProcessor.iteritems():
        buildMaster.dispatchByProcessor(processor, buildCandidates)

    return result_code


if __name__ == '__main__':
    parser = OptionParser()
    logger_options(parser)
    (options, arguments) = parser.parse_args()

    if arguments:
        parser.error("Unhandled arguments %s" % repr(arguments))
    execute_zcml_for_scripts()

    log = logger(options, 'slavescanner')

    log.info("Slave Scan Process Initiated.")

    locker = GlobalLock(_default_lockfile, logger=log)
    try:
        locker.acquire()
    except GlobalLockError:
        log.info("Cannot acquire lock.")
        # XXX cprov 20060625: do not scream on lock conflicts during the
        # edgy rebuild time.
        sys.exit(0)

    result_code = 0
    try:
        result_code = max(result_code, doSlaveScan(log))
    finally:
        # release process lock file if the procedure finished properly
        locker.release()

    log.info("Slave Scan Process Finished.")

    sys.exit(result_code)
