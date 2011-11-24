#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Archive Override Check

Given a distribution to run on, report any override inconsistence found.
It basically check if all published source and binaries are coherent.
"""

import _pythonpath

import transaction
from zope.component import getUtility

from canonical.config import config
from lp.app.errors import NotFoundError
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.scripts.base import LaunchpadScript
from lp.soyuz.scripts.ftpmaster import PubSourceChecker
from lp.soyuz.enums import PackagePublishingStatus


class ArchiveOverrideCheckScript(LaunchpadScript):

    def add_my_options(self):
        self.parser.add_option(
            "-d", "--distribution", action="store",
            dest="distribution", metavar="DISTRO", default="ubuntu",
            help="Distribution to consider")
        self.parser.add_option(
            "-s", "--suite", action="store",
            dest="suite", metavar="SUITE", default=None,
            help=("Suite to consider, if not passed consider the "
                  "currentseries and the RELEASE pocket"))

    def main(self):
        try:
            try:
                distribution = getUtility(IDistributionSet)[
                    self.options.distribution]
                if self.options.suite is None:
                    distroseries = distribution.currentseries
                    pocket = PackagePublishingPocket.RELEASE
                else:
                    distroseries, pocket = (
                        distribution.getDistroSeriesAndPocket(
                            self.options.suite))

                self.logger.debug(
                    "Considering: %s/%s/%s/%s."
                    % (distribution.name, distroseries.name, pocket.name,
                       distroseries.status.name))

                checkOverrides(distroseries, pocket, self.logger)
            except NotFoundError, info:
                self.logger.error('Not found: %s' % info)
        finally:
            self.logger.debug("Rolling back any remaining transactions.")
            transaction.abort()


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
    script = ArchiveOverrideCheckScript(
        'archive-override-check', config.archivepublisher.dbuser)
    script.lock_and_run()
