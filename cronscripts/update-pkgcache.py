#!/usr/bin/python2.4

# Copyright 2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

# This script updates the cached source package information in the system.
# We use this for fast source package searching (as opposed to joining
# through gazillions of publishing tables).

import _pythonpath

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces import (
    ArchivePurpose, IDistributionSet)
from canonical.database.sqlbase import ISOLATION_LEVEL_READ_COMMITTED
from canonical.launchpad.scripts.base import LaunchpadCronScript


class PackageCacheUpdater(LaunchpadCronScript):
    """Helper class for updating package caches.

    It iterates over all distributions, distroseries and archives (including
    PPAs) updating the package caches to reflect what is currently published
    in those locations.
    """

    def updateDistributionPackageCounters(self, distribution):
        """Update package counters for a given distribution."""
        for distroseries in distribution:
            distroseries.updatePackageCount()
            self.txn.commit()
            for arch in distroseries.architectures:
                arch.updatePackageCount()
                self.txn.commit()

    def updateDistributionCache(self, distribution, archive):
        """Update package caches for the given location.

        'archive' can be one of the main archives (PRIMARY, PARTNER or
        EMBARGOED) or even a PPA.

        This method commits the transaction frequently since it deal with
        a huge amount of data.

        PPA archives caches are consolidated in a Archive row to optimize
        searches across PPAs.
        """
        for distroseries in distribution.serieses:
            self.updateDistroSeriesCache(distroseries, archive)

        distribution.removeOldCacheItems(archive, log=self.logger)
        self.txn.commit()

        distribution.updateCompleteSourcePackageCache(
            archive=archive, ztm=self.txn, log=self.logger)
        self.txn.commit()

        # Only PPAs package counters are cached in the Archive records,
        # PRIMARY and PARTNER counter are already stored in DistroSeries
        # and DistroArchSeries records.
        if archive.purpose == ArchivePurpose.PPA:
            archive.updateArchiveCache()
            self.txn.commit()

    def updateDistroSeriesCache(self, distroseries, archive):
        """Update package caches for the given location."""
        self.logger.info('%s %s %s starting' % (
            distroseries.distribution.name, distroseries.name, archive.title))

        distroseries.removeOldCacheItems(archive=archive, log=self.logger)
        self.txn.commit()

        distroseries.updateCompletePackageCache(
            archive=archive, ztm=self.txn, log=self.logger)
        self.txn.commit()

    def main(self):
        self.txn.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
        self.logger.debug('Starting the package cache update')

        # Do the package counter and cache update.
        distroset = getUtility(IDistributionSet)
        for distribution in distroset:
            self.logger.info(
                'Updating %s package counters' % distribution.name)
            self.updateDistributionPackageCounters(distribution)

            self.logger.info(
                'Updating %s main archives' % distribution.name)
            for archive in distribution.all_distro_archives:
                self.updateDistributionCache(distribution, archive)

            self.logger.info(
                'Updating %s PPAs' % distribution.name)
            for archive in distribution.getAllPPAs():
                self.updateDistributionCache(distribution, archive)

            self.logger.info('%s done' % distribution.name)

        self.logger.debug('Finished the package cache update')

if __name__ == '__main__':
    script = PackageCacheUpdater(
        'update-cache', dbuser=config.statistician.dbuser)
    script.lock_and_run()

