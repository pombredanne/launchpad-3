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


def doSlaveScan(tm):
    """Proceed the Slave Scanning Process."""    
    buildMaster = BuilddMaster(logging.getLogger(), tm)

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
            #logging.getLogger().warn(info, exc_info=1)
            logging.getLogger().warn(info)
                
    # Scan all the pending builds; update logtails; retrieve
    # builds where they are compled
    buildMaster.scanActiveBuilders()
        
    # Now that the slaves are free, ask the buildmaster to calculate
    # the set of build candiates
    buildCandidatesSortedByProcessor = buildMaster.sortAndSplitByProcessor()
    
    # Now that we've gathered in all the builds;
    # dispatch the pending ones
    for processor, buildCandidates in \
            buildCandidatesSortedByProcessor.iteritems():
        buildMaster.dispatchByProcessor(processor, buildCandidates)

        
def main(tm):
    """Simple wrap SlaveScan."""
    # Build master logging set
    #logging.basicConfig(filename=_default_logfilename)
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger().debug("Initialising Slave Scan Process")

    locker = LockFile(_default_lockfile)

    try:
        locker.acquire()
    except OSError:
        logging.getLogger().info("Cannot acquire lock.")
        sys.exit(1)

    try:
        doSlaveScan(tm)
    finally:
        # release process lock file if the procedure finished properly
        locker.release()

if __name__ == '__main__':
    # setup a transaction manager
    tm = initZopeless(dbuser='fiera')
    # wooo, we have a main :)
    main(tm)
    
