#!/usr/bin/python2.4
"""Queue/Accepted processor

Given a distribution to run on, obtains all the queue items for the
distribution and then gets on and deals with any accepted items, preparing them
for publishing as appropriate.
"""

import _pythonpath

import sys
from optparse import OptionParser

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces import IDistributionSet
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.launchpad.scripts.processaccepted import close_bugs
from canonical.lp import (
    initZopeless, READ_COMMITTED_ISOLATION)

from contrib.glock import GlobalLock
from canonical.lp.dbschema import PackageUploadStatus

def main():
    # Parse command-line arguments
    parser = OptionParser()
    logger_options(parser)

    parser.add_option("-n", "--dry-run", action="store_true",
                      dest="dryrun", metavar="DRY_RUN", default=False,
                      help="Whether to treat this as a dry-run or not.")

    parser.add_option("--ppa", action="store_true",
                      dest="ppa", metavar="PPA", default=False,
                      help="Run only over PPA archives.")

    (options, args) = parser.parse_args()

    log = logger(options, "process-accepted")

    if len(args) != 1:
        log.error("Need to be given exactly one non-option argument. "
                  "Namely the distribution to process.")
        return 1

    distro_name = args[0]

    log.debug("Acquiring lock")
    lock = GlobalLock('/var/lock/launchpad-upload-queue.lock')
    lock.acquire(blocking=True)

    log.debug("Initialising connection.")

    ztm = initZopeless(
        dbuser=config.uploadqueue.dbuser, isolation=READ_COMMITTED_ISOLATION)
    execute_zcml_for_scripts()

    processed_queue_ids = []
    try:
        log.debug("Finding distribution %s." % distro_name)
        distribution = getUtility(IDistributionSet).getByName(distro_name)

        # target_archives is a tuple of (archive, description).
        if options.ppa:
            target_archives = [
                (archive, archive.archive_url)
                for archive in distribution.getPendingAcceptancePPAs()]
        else:
            target_archives = [
                (archive, archive.purpose.title)
                for archive in distribution.all_distro_archives]

        for archive, description in target_archives:
            for distrorelease in distribution.serieses:

                log.debug("Processing queue for %s %s" % (
                        distrorelease.name, description))

                queue_items = distrorelease.getQueueItems(
                    PackageUploadStatus.ACCEPTED, archive=archive)
                for queue_item in queue_items:
                    try:
                        queue_item.realiseUpload(log)
                    except:
                        log.error("Failure processing queue_item %d"
                                  % (queue_item.id), exc_info=True)
                        raise
                    else:
                        processed_queue_ids.append(queue_item.id)

        if not options.dryrun:
            ztm.commit()
        else:
            log.debug("Dry Run mode.")

        log.debug("Closing bugs.")
        close_bugs(processed_queue_ids)

        if not options.dryrun:
            ztm.commit()

    finally:
        log.debug("Rolling back any remaining transactions.")
        ztm.abort()
        log.debug("Releasing lock")
        lock.release()

    return 0

if __name__ == '__main__':
    sys.exit(main())

