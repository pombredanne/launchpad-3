#!/usr/bin/env python2.4
# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Automatically give back MANUALDEPWAIT build records."""

import _pythonpath

import logging
import sys
import time

from optparse import OptionParser

from zope.component import getUtility

from canonical.lp import initZopeless, dbschema
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, logger)

from canonical.launchpad.scripts.lockfile import LockFile
from canonical.launchpad.interfaces import IBuildSet, IDistributionSet

MANUALDEPWAIT = dbschema.BuildStatus.MANUALDEPWAIT

HOUR = 60
DAY = HOUR * 24

def minutes_since(timestamp):
    """Return the number of minutes since the given timestamp."""
    return (time.time() - time.mktime(timestamp.timetuple())) / 60

def main():
    options_parser = OptionParser()
    logger_options(options_parser)

    options_parser.add_option(
        "-d", "--distro", action="store", type="string", dest="distro",
        metavar="DISTRO", help="Distribution to give back from",
        default="ubuntu")
    options_parser.add_option(
        "-m", "--minage", action="store", type="int", dest="minage",
        metavar="MINAGE", help="Minimum age in minutes before give-back",
        default=8*HOUR)
    options_parser.add_option(
        "-M", "--maxage", action="store", type="int", dest="maxage",
        metavar="MAXAGE",
        help="Maximum age in minutes before we don't give-back",
        default=3*DAY)
    
    options, args = options_parser.parse_args(sys.argv)

    log = logger(options, 'auto-giveback')

    lockfile = LockFile('/var/lock/launchpad-auto-giveback.lock', logger=log)
    lockfile.acquire()

    try:
        log.info("Initialising...")
        ztm = initZopeless(dbuser="fiera")
        log.info("Executing ZCML...")
        execute_zcml_for_scripts()

        log.info("Finding distribution '%s'..." % options.distro)
        distro = getUtility(IDistributionSet)[options.distro]
        log.info("Finding builds in MANUALDEPWAIT...")
        build_utility = getUtility(IBuildSet)
        builds = build_utility.getBuildsForDistribution(distro, MANUALDEPWAIT)
        log.info("Changing builds to NEEDSBUILD...")
        changed_build_count = 0
        for build in builds:
            full_age = minutes_since(build.datecreated)
            since_last_build = minutes_since(build.datebuilt)
            if (since_last_build >= options.minage and
                full_age <= options.maxage):
                build.buildstate = dbschema.BuildStatus.NEEDSBUILD
                changed_build_count += 1
        log.info("Changed %d" % changed_build_count)
        log.info("Committing...")
        ztm.commit()
        log.info("Done.")
        
    finally:
        lockfile.release()

if __name__ == "__main__":
    main()
