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
from optparse import OptionParser

from zope.component import getUtility

from canonical.lp import initZopeless
from canonical.launchpad.interfaces import IDistroArchReleaseSet

from canonical.launchpad.scripts.builddmaster import BuilddMaster
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.launchpad.scripts import (
        execute_zcml_for_scripts, logger_options, logger
        )

_default_lockfile = '/var/lock/buildd-master.lock'

def doSlaveScan(logger):
    """Proceed the Slave Scanning Process."""    
    # XXX cprov 20051019
    # retrive the user infromation from the config file
    
    # setup a transaction manager
    tm = initZopeless(dbuser='fiera')

    buildMaster = BuilddMaster(logger, tm)

    logger.info("Setting Builders.")
    
    # For every distroarchrelease we can find;
    # put it into the build master
    for archrelease in getUtility(IDistroArchReleaseSet):
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

if __name__ == '__main__':
    parser = OptionParser()
    logger_options(parser)
    (options, arguments) = parser.parse_args()

    if arguments:
        parser.error("Unhandled arguments %s" % repr(arguments))
    execute_zcml_for_scripts()

    log = logger(options, 'slavescanner')

    log.info("Slave Scan Process Initiated.")

    locker = LockFile(_default_lockfile, logger=log)
    try:
        locker.acquire()
    except OSError:
        logger.info("Cannot acquire lock.")
        sys.exit(1)

    try:
        doSlaveScan(log)
    finally:
        # release process lock file if the procedure finished properly
        locker.release()

    log.info("Slave Scan Process Finished.")
