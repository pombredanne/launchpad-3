#!/usr/bin/python2.4

# Copyright Canonical Limited 2006

"""Tool for 'mass-retrying' build records.

It supports build collections based distroseries and/or distroarchseries.
"""

__metaclass__ = type

import _pythonpath

from optparse import OptionParser
import sys

from zope.component import getUtility

from canonical.database.sqlbase import ISOLATION_LEVEL_READ_COMMITTED
from canonical.launchpad.interfaces import (
    BuildStatus, IDistributionSet, NotFoundError, PackagePublishingPocket)
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, logger)
from canonical.lp import initZopeless


def main():
    parser = OptionParser()
    logger_options(parser)

    parser.add_option("-d", "--distribution",
                      dest="distribution", metavar="DISTRIBUTION",
                      default="ubuntu", help="distribution name")

    parser.add_option("-s", "--suite",
                      dest="suite", metavar="SUITE", default=None,
                      help="suite name")

    parser.add_option("-a", "--architecture",
                      dest="architecture", metavar="ARCH", default=None,
                      help="architecture tag")

    parser.add_option("-N", "--dry-run", action="store_true",
                      dest="dryrun", metavar="DRY_RUN", default=False,
                      help="Whether to treat this as a dry-run or not.")

    parser.add_option("-F", "--failed", action="store_true",
                      dest="failed", default=False,
                      help="Reset builds in FAILED state.")

    parser.add_option("-D", "--dep-wait", action="store_true",
                      dest="depwait", default=False,
                      help="Reset builds in DEPWAIT state.")

    parser.add_option("-C", "--chroot-wait", action="store_true",
                      dest="chrootwait", default=False,
                      help="Reset builds in CHROOTWAIT state.")

    (options, args) = parser.parse_args()

    log = logger(options, "build-mass-retry")

    log.debug("Intitialising connection.")
    ztm = initZopeless(dbuser="fiera",
                       isolation=ISOLATION_LEVEL_READ_COMMITTED)
    execute_zcml_for_scripts()

    try:
        distribution = getUtility(IDistributionSet)[options.distribution]
    except NotFoundError, info:
        log.error("Distribution not found: %s" % info)
        return 1

    try:
        if options.suite is not None:
            series, pocket = distribution.getDistroSeriesAndPocket(
                options.suite)
        else:
            series = distribution.currentseries
            pocket = PackagePublishingPocket.RELEASE
    except NotFoundError, info:
        log.error("Suite not found: %s" % info)
        return 1

    # store distroseries as the current IHasBuildRecord provider
    build_provider = series

    if options.architecture:
        try:
            dar = series[options.architecture]
        except NotFoundError, info:
            log.error(info)
            return 1

        # store distroarchseries as the current IHasBuildRecord provider
        build_provider = dar

    log.info("Initialising Build Mass-Retry for '%s/%s'"
              % (build_provider.title, pocket.name))

    requested_states_map = {
        BuildStatus.FAILEDTOBUILD : options.failed,
        BuildStatus.MANUALDEPWAIT : options.depwait,
        BuildStatus.CHROOTWAIT : options.chrootwait,
        }

    # XXX cprov 2006-08-31: one query per requested state
    # could organise it in a single one nicely if I have
    # an empty SQLResult instance, than only iteration + union()
    # would work.
    for target_state, requested in requested_states_map.items():
        if not requested:
            continue

        log.info("Processing builds in '%s'" % target_state.title)
        target_builds = build_provider.getBuildRecords(
            build_state=target_state, pocket=pocket)

        for build in target_builds:

            if not build.can_be_retried:
                log.warn('Can not retry %s (%s)' % (build.title, build.id))
                continue

            log.info('Retrying %s (%s)' % (build.title, build.id))
            build.retry()

    log.info("Success.")

    if options.dryrun:
        ztm.abort()
        log.info('Dry-run.')
    else:
        ztm.commit()
        log.info("Committed")

    return 0


if __name__ == '__main__':
    sys.exit(main())
