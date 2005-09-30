#!/usr/bin/env python
# Copyright 2004 Canonical Ltd.  All rights reserved.
# Author: Daniel Silverstone <daniel.silverstone@canonical.com>
#         Celso Providelo <celso.providelo@canonical.com>
#
# Build Jobs initialization
# 
__metaclass__ = type

import sys
import logging

from canonical.lp import initZopeless
from canonical.launchpad.database import DistroArchRelease

from canonical.launchpad.scripts.builddmaster import BuilddMaster

from canonical.launchpad.scripts.lockfile import LockFile


_default_lockfile = '/var/lock/buildd-master.lock'
_default_logfilename = '/var/tmp/queuebuilder.log'


def rebuildQueue(logger, tm):
    """Look for and initialise new build jobs."""

    buildMaster = BuilddMaster(logger, tm)

    # Simple container
    distroreleases = set()
        
    # For every distroarchrelease we can find; put it into the build master
    for archrelease in DistroArchRelease.select():
        distroreleases.add(archrelease.distrorelease)
        buildMaster.addDistroArchRelease(archrelease)
        
    # For each distrorelease we care about; scan for sourcepackagereleases
    # with no build associated with the distroarchreleases we're
    # interested in
    for distrorelease in distroreleases:
        buildMaster.createMissingBuilds(distrorelease)
    
    # For each build record in NEEDSBUILD, ensure it has a
    #buildqueue entry
    buildMaster.addMissingBuildQueueEntries()
                
    #Rescore the NEEDSBUILD properly
    buildMaster.sanitiseAndScoreCandidates()

def make_logger(loglevel=logging.WARN):
    """Return a logger object for logging with."""
    logger = logging.getLogger("buildd-queue-builder")
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
        logger.info("Cannot Acquire Lock.")
        sys.exit(1)

    try:
        rebuildQueue(logger, tm)
    finally:
        locker.release()
    
    logger.info("Buildd Queue Rebuilt.")
