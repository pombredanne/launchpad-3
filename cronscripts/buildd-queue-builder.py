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


_default_lockfile = '/var/lock/queuebuilder.lock'
_default_logfilename = '/var/tmp/queuebuilder.log'


def rebuildQueue(tm):
    """Look for and initialise new build jobs."""

    buildMaster = BuilddMaster(logging.getLogger('queuebuilder'), tm)

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

def main(tm):
    # logging setup
    #logging.basicConfig(filename=_default_logfilename)
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger().debug("Initialising BuildQueue Builder")

    locker = LockFile(_default_lockfile)
    
    try:
        locker.acquire()
    except OSError:
        logging.getLogger().info("Cannot Acquire Lock.")
        sys.exit(1)

    try:
        rebuildQueue(tm)
    finally:
        locker.release()

if __name__ == '__main__':
    # setup a transaction manager
    tm = initZopeless(dbuser='fiera')
    main(tm)

