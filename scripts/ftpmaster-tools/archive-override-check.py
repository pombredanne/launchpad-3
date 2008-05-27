#!/usr/bin/python2.4
"""Archive Override Check

Given a distribution to run on, report any override inconsistence found.
It basically check if all published source and binaries are coherent.
"""

import _pythonpath

from optparse import OptionParser
import sys

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.launchpad.scripts.ftpmaster import  PubSourceChecker
from canonical.launchpad.interfaces import (
    IDistributionSet, NotFoundError, PackagePublishingStatus,
    PackagePublishingPocket)
from canonical.lp import initZopeless

from contrib.glock import GlobalLock

def main():
    # Parse command-line arguments
    parser = OptionParser()
    logger_options(parser)

    parser.add_option("-d", "--distribution", action="store",
                      dest="distribution", metavar="DISTRO", default="ubuntu",
                      help="Distribution to consider")

    parser.add_option("-s", "--suite", action="store",
                      dest="suite", metavar="SUITE", default=None,
                      help=("Suite to consider, if not passed consider the "
                            "currentseries and the RELEASE pocket"))

    (options, args) = parser.parse_args()

    log = logger(options, "archive-override-check")

    log.debug("Acquiring lock")
    lock = GlobalLock('/var/lock/archive-override-check.lock')
    lock.acquire(blocking=True)

    log.debug("Initialising connection.")
    execute_zcml_for_scripts()
    ztm = initZopeless(dbuser=config.archivepublisher.dbuser)

    try:
        try:
            distribution = getUtility(IDistributionSet)[options.distribution]
            if options.suite is None:
                distroseries = distribution.currentseries
                pocket = PackagePublishingPocket.RELEASE
            else:
                distroseries, pocket = distribution.getDistroSeriesAndPocket(
                    options.suite)

            log.debug("Considering: %s/%s/%s/%s."
                      % (distribution.name, distroseries.name, pocket.name,
                         distroseries.status.name))

            checkOverrides(distroseries, pocket, log)

        except NotFoundError, info:
            log.error('Not found: %s' % info)

    finally:
        log.debug("Rolling back any remaining transactions.")
        ztm.abort()
        log.debug("Releasing lock")
        lock.release()

    return 0


def checkOverrides(distroseries, pocket, log):
    """Initialize and handle PubSourceChecker.

    Iterate over PUBLISHED sources and perform PubSourceChecker.check()
    on each published Source/Binaries couple.
    """
    spps = distroseries.getSourcePackagePublishing(
        status=PackagePublishingStatus.PUBLISHED,
        pocket=pocket)

    log.debug('%s published sources' % spps.count())

    for spp in spps:
        spr = spp.sourcepackagerelease
        checker = PubSourceChecker(
            spr.name, spr.version, spp.component.name, spp.section.name,
            spr.urgency.name)

        for bpp in spp.getPublishedBinaries():
            bpr = bpp.binarypackagerelease
            checker.addBinary(
                bpr.name, bpr.version, bpp.distroarchseries.architecturetag,
                bpp.component.name, bpp.section.name, bpr.priority.name)

        checker.check()

        report = checker.renderReport()

        if report:
            print report

if __name__ == '__main__':
    sys.exit(main())

