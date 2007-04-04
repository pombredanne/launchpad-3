#!/usr/bin/python2.4
"""Initialise a new distrorelease from its parent

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

from canonical.database.sqlbase import (
    sqlvalues, flush_database_updates, cursor, flush_database_caches)
from canonical.lp import (
    initZopeless, READ_COMMITTED_ISOLATION)
from canonical.lp.dbschema import (
    DistroReleaseQueueStatus, BuildStatus, PackagePublishingPocket)
from canonical.launchpad.interfaces import (
    IDistributionSet, NotFoundError)
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
                  "Namely the distrorelease to initialise.")
        return 1

    distrorelease_name = args[0]

    log.debug("Acquiring lock")
    lock = GlobalLock('/var/lock/launchpad-initialise.lock')
    lock.acquire(blocking=True)

    log.debug("Initialising connection.")

    ztm = initZopeless(dbuser='lucille', isolation=READ_COMMITTED_ISOLATION)
    execute_zcml_for_scripts()

    try:
        # 'ubuntu' is the default option.distribution value
        distribution = getUtility(IDistributionSet)[options.distribution]
        distrorelease = distribution[distrorelease_name]
    except NotFoundError, info:
        log.error(info)
        return 1

    # XXX cprov 20060526: these two extra functions must be
    # integrated in IDistroRelease.initialiseFromParent workflow.
    log.debug('Check empty mutable queues in parentrelease')
    check_queue(distrorelease)

    log.debug('Check for no pending builds in parentrelease')
    check_builds(distrorelease)

    log.debug('Copying distroarchreleases from parent '
              'and setting nominatedarchindep.')
    copy_architectures(distrorelease)

    log.debug('initialising from parent, copying publishing records.')
    distrorelease.initialiseFromParent()

    if options.dryrun:
        log.debug('Dry-Run mode, transaction aborted.')
        ztm.abort()
    else:
        log.debug('Committing transaction.')
        ztm.commit()

    log.debug("Releasing lock")
    lock.release()
    return 0


def check_builds(distrorelease):
    """Assert there are no pending builds for parent release.

    Only cares about the RELEASE pocket, which is the only one inherited
    via initialiseFromParent method.
    """
    parentrelease = distrorelease.parentrelease

    # only the RELEASE pocket is inherited, so we only check
    # pending build records for it.
    pending_builds = parentrelease.getBuildRecords(
        BuildStatus.NEEDSBUILD, pocket=PackagePublishingPocket.RELEASE)

    assert (pending_builds.count() == 0,
            'Parent must not have PENDING builds')

def check_queue(distrorelease):
    """Assert upload queue is empty on parent release.

    Only cares about the RELEASE pocket, which is the only one inherited
    via initialiseFromParent method.
    """
    parentrelease = distrorelease.parentrelease

    # only the RELEASE pocket is inherited, so we only check
    # queue items for it.
    new_items = parentrelease.getQueueItems(
        DistroReleaseQueueStatus.NEW,
        pocket=PackagePublishingPocket.RELEASE)
    accepted_items = parentrelease.getQueueItems(
        DistroReleaseQueueStatus.ACCEPTED,
        pocket=PackagePublishingPocket.RELEASE)
    unapproved_items = parentrelease.getQueueItems(
        DistroReleaseQueueStatus.UNAPPROVED,
        pocket=PackagePublishingPocket.RELEASE)

    assert (new_items.count() == 0,
            'Parent NEW queue must be empty')
    assert (accepted_items.count() == 0,
            'Parent ACCEPTED queue must be empty')
    assert (unapproved_items.count() == 0,
            'Parent UNAPPROVED queue must be empty')

def copy_architectures(distrorelease):
    """Overlap SQLObject and copy architecture from the parent.

    Also set the nominatedarchindep properly in target.
    """
    assert distrorelease.architectures.count() is 0, (
        "Can not copy distroarchreleases from parent, there are already "
        "distroarchrelease(s) initialised for this release.")
    flush_database_updates()
    cur = cursor()
    cur.execute("""
    INSERT INTO DistroArchRelease
          (distrorelease, processorfamily, architecturetag, owner, official)
    SELECT %s, processorfamily, architecturetag, %s, official
    FROM DistroArchRelease WHERE distrorelease = %s
    """ % sqlvalues(distrorelease, distrorelease.owner,
                    distrorelease.parentrelease))
    flush_database_caches()

    distrorelease.nominatedarchindep = distrorelease[
        distrorelease.parentrelease.nominatedarchindep.architecturetag]


if __name__ == '__main__':
    sys.exit(main())

