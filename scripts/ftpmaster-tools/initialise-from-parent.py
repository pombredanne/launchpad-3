#!/usr/bin/python2.4
"""Initialise a new distroseries from its parent

It performs two additional tasks before call initialiseFromParent:

* check_queue (ensure parent's mutable queues are empty)
* copy_architectures (copy parent's architectures and set
                      nominatedarchindep properly)

which eventually may be integrated in its workflow.
"""

import _pythonpath

import sys
from optparse import OptionParser

from zope.component import getUtility
from contrib.glock import GlobalLock

from canonical.config import config
from canonical.database.sqlbase import (
    sqlvalues, flush_database_updates, cursor, flush_database_caches)
from canonical.lp import initZopeless
from canonical.launchpad.interfaces import (
    BuildStatus, IDistributionSet, NotFoundError, PackageUploadStatus,
    PackagePublishingPocket)
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)


def main():
    # Parse command-line arguments
    parser = OptionParser()
    logger_options(parser)

    parser.add_option("-N", "--dry-run", action="store_true",
                      dest="dryrun", metavar="DRY_RUN", default=False,
                      help="Whether to treat this as a dry-run or not.")

    parser.add_option("-d", "--distro", dest="distribution", metavar="DISTRO",
                      default="ubuntu",
                      help="Distribution name")

    (options, args) = parser.parse_args()

    log = logger(options, "initialise")

    if len(args) != 1:
        log.error("Need to be given exactly one non-option argument. "
                  "Namely the distroseries to initialise.")
        return 1

    distroseries_name = args[0]

    log.debug("Acquiring lock")
    lock = GlobalLock('/var/lock/launchpad-initialise.lock')
    lock.acquire(blocking=True)

    log.debug("Initialising connection.")

    ztm = initZopeless(dbuser=config.archivepublisher.dbuser)
    execute_zcml_for_scripts()

    try:
        # 'ubuntu' is the default option.distribution value
        distribution = getUtility(IDistributionSet)[options.distribution]
        distroseries = distribution[distroseries_name]
    except NotFoundError, info:
        log.error(info)
        return 1

    # XXX cprov 2006-05-26: these two extra functions must be
    # integrated in IDistroSeries.initialiseFromParent workflow.
    log.debug('Check empty mutable queues in parentseries')
    check_queue(distroseries)

    log.debug('Check for no pending builds in parentseries')
    check_builds(distroseries)

    log.debug('Copying distroarchserieses from parent '
              'and setting nominatedarchindep.')
    copy_architectures(distroseries)

    log.debug('initialising from parent, copying publishing records.')
    distroseries.initialiseFromParent()

    if options.dryrun:
        log.debug('Dry-Run mode, transaction aborted.')
        ztm.abort()
    else:
        log.debug('Committing transaction.')
        ztm.commit()

    log.debug("Releasing lock")
    lock.release()
    return 0


def check_builds(distroseries):
    """Assert there are no pending builds for parent series.

    Only cares about the RELEASE pocket, which is the only one inherited
    via initialiseFromParent method.
    """
    parentseries = distroseries.parentseries

    # only the RELEASE pocket is inherited, so we only check
    # pending build records for it.
    pending_builds = parentseries.getBuildRecords(
        BuildStatus.NEEDSBUILD, pocket=PackagePublishingPocket.RELEASE)

    assert (pending_builds.count() == 0,
            'Parent must not have PENDING builds')

def check_queue(distroseries):
    """Assert upload queue is empty on parent series.

    Only cares about the RELEASE pocket, which is the only one inherited
    via initialiseFromParent method.
    """
    parentseries = distroseries.parentseries

    # only the RELEASE pocket is inherited, so we only check
    # queue items for it.
    new_items = parentseries.getQueueItems(
        PackageUploadStatus.NEW,
        pocket=PackagePublishingPocket.RELEASE)
    accepted_items = parentseries.getQueueItems(
        PackageUploadStatus.ACCEPTED,
        pocket=PackagePublishingPocket.RELEASE)
    unapproved_items = parentseries.getQueueItems(
        PackageUploadStatus.UNAPPROVED,
        pocket=PackagePublishingPocket.RELEASE)

    assert (new_items.count() == 0,
            'Parent NEW queue must be empty')
    assert (accepted_items.count() == 0,
            'Parent ACCEPTED queue must be empty')
    assert (unapproved_items.count() == 0,
            'Parent UNAPPROVED queue must be empty')

def copy_architectures(distroseries):
    """Overlap SQLObject and copy architecture from the parent.

    Also set the nominatedarchindep properly in target.
    """
    assert distroseries.architectures.count() is 0, (
        "Can not copy distroarchseries from parent, there are already "
        "distroarchseries(s) initialised for this series.")
    flush_database_updates()
    cur = cursor()
    cur.execute("""
    INSERT INTO DistroArchSeries
          (distroseries, processorfamily, architecturetag, owner, official)
    SELECT %s, processorfamily, architecturetag, %s, official
    FROM DistroArchSeries WHERE distroseries = %s
    """ % sqlvalues(distroseries, distroseries.owner,
                    distroseries.parentseries))
    flush_database_caches()

    distroseries.nominatedarchindep = distroseries[
        distroseries.parentseries.nominatedarchindep.architecturetag]


if __name__ == '__main__':
    sys.exit(main())

