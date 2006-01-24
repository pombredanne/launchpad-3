#!/usr/bin/env python
"""Queue/Accepted processor

Given a distribution to run on, obtains all the queue items for the
distribution and then gets on and deals with any accepted items, preparing them
for publishing as appropriate.
"""

import _pythonpath

import os
import sys

from optparse import OptionParser

from zope.component import getUtility

from canonical.lp import initZopeless
from canonical.config import config
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.launchpad.interfaces import IDistributionSet

from contrib.glock import GlobalLock
from canonical.lp.dbschema import DistroReleaseQueueStatus

def main():
    # Parse command-line arguments
    parser = OptionParser()
    logger_options(parser)

    parser.add_option("-N", "--dry-run", action="store_true",
                      dest="dryrun", metavar="DRY_RUN", default=False,
                      help="Whether to treat this as a dry-run or not.")
    global options
    (options, args) = parser.parse_args()

    global log
    log = logger(options, "process-accepted")

    if len(args) != 1:
        log.error("Need to be given exactly one non-option argument. "
                  "Namely the distribution to process.")
        return 1

    distro_name = args[0]

    log.debug("Acquiring lock")
    lock = GlobalLock('/var/lock/launchpad-process-accepted.lock')
    lock.acquire(blocking=True)

    log.debug("Initialising connection.")
    global ztm
    ztm = initZopeless(dbuser=config.uploadqueue.dbuser)

    execute_zcml_for_scripts()

    try:
        log.debug("Finding distribution %s." % distro_name)
        distro = getUtility(IDistributionSet).getByName(distro_name)
        for release in distro.releases:
            log.debug("Processing queue for %s" % release.name)
            queue_items = release.getQueueItems(
                DistroReleaseQueueStatus.ACCEPTED)
            for queue_item in queue_items:
                try:
                    queue_item.realiseUpload(log)
                    ztm.commit()
                except: # Re-raised after logging.
                    log.error("Failure processing queue_item %d" % (
                        queue_item.id))
                    raise
                
    finally:
        log.debug("Rolling back any remaining transactions.")
        ztm.abort()
        log.debug("Releasing lock")
        lock.release()

    return 0

if __name__ == '__main__':
    sys.exit(main())

