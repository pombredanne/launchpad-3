#!/usr/bin/env python
# Copyright 2004 Canonical Ltd.  All rights reserved.
# Author: Daniel Silverstone <daniel.silverstone@canonical.com>
#         Celso Providelo <celso.providelo@canonical.com>
#
# Builder Slave Scanner and result collector

__metaclass__ = type

import sys
import logging
import os

from canonical.lp import initZopeless
from canonical.launchpad.database import DistroArchRelease

from canonical.launchpad.scripts.builddmaster import BuilddMaster
from canonical.launchpad.scripts.lockfile import LockFile


_default_lockfile = '/var/lock/buildd-slave-scanner.lock'
_default_logfilename = '/var/tmp/buildd-slave-scanner.log'


def doSlaveScan(logger, tm):
    """Proceed the Slave Scanning Process."""    
    buildMaster = BuilddMaster(logger, tm)

    logger.info("Setting Builders.")
    # For every distroarchrelease we can find;
    # put it into the build master
    for archrelease in DistroArchRelease.select():
        buildMaster.addDistroArchRelease(archrelease)
        try:
            buildMaster.setupBuilders(archrelease)
        except KeyError, key:
            info = ("Unable to setup builder for %s/%s/%s."
                    % (archrelease.distrorelease.distribution.name,
                       archrelease.distrorelease.name,
                       archrelease.architecturetag))
            # less is more, noisely verbose
            #logger.warn(info, exc_info=1)
            logger.warn(info)

    logger.info("Scanning Builders.")
    # Scan all the pending builds; update logtails; retrieve
    # builds where they are compled
    buildMaster.scanActiveBuilders()

    # Now that the slaves are free, ask the buildmaster to calculate
    # the set of build candiates
    buildCandidatesSortedByProcessor = buildMaster.sortAndSplitByProcessor()
    
    logger.info("Dispatching Jobs.")
    # Now that we've gathered in all the builds;
    # dispatch the pending ones
    for processor, buildCandidates in \
            buildCandidatesSortedByProcessor.iteritems():
        buildMaster.dispatchByProcessor(processor, buildCandidates)

def make_logger(loglevel=logging.WARN):
    """Return a logger object for logging with."""
    logger = logging.getLogger("buildd-slave-scanner")
    handler = logging.StreamHandler(strm=sys.stderr)
    handler.setFormatter(
        logging.Formatter(fmt='%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(loglevel)
    return logger


if __name__ == '__main__':
    # setup a transaction manager
    tm = initZopeless(dbuser='fiera')
    logger = make_logger(loglevel=logging.DEBUG)
    locker = LockFile(_default_lockfile)

    try:
        locker.acquire()
    except OSError:
        logger.info("Cannot acquire lock.")
        sys.exit(1)

    try:
        doSlaveScan(logger, tm)
    finally:
        # release process lock file if the procedure finished properly
        locker.release()

    logger.info("Slave Scan Process Finished.")
