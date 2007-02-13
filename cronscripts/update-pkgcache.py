#!/usr/bin/env python

# Copyright 2005 Canonical Ltd.  All rights reserved.

# This script updates the cached source package information in the system.
# We use this for fast source package searching (as opposed to joining
# through gazillions of publishing tables).

import _pythonpath

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces import IDistributionSet
from canonical.launchpad.scripts.base import LaunchpadScript
from canonical.lp import READ_COMMITTED_ISOLATION


class PackageCacheUpdater(LaunchpadScript):
    def updateDistroReleaseCache(self, distrorelease):
        self.logger.info('%s starting' % distrorelease.name)
        distrorelease.updatePackageCount()
        self.txn.commit()
        distrorelease.removeOldCacheItems(log=self.logger)
        self.txn.commit()
        distrorelease.updateCompletePackageCache(
            ztm=self.txn, log=self.logger)
        self.txn.commit()
        for arch in distrorelease.architectures:
            arch.updatePackageCount()
            self.txn.commit()

    def main(self):
        self.txn.set_isolation_level(READ_COMMITTED_ISOLATION)
        self.logger.debug('Starting the sp cache update')
        # Do the cache update
        distroset = getUtility(IDistributionSet)
        for distro in distroset:
            for distrorelease in distro.releases:
                self.updateDistroReleaseCache(distrorelease)
            distro.removeOldCacheItems(log=self.logger)
            self.txn.commit()
            distro.updateCompleteSourcePackageCache(ztm=self.txn,
                                                    log=self.logger)
            self.txn.commit()
            self.logger.info('%s done' % distro.name)
        self.logger.debug('Finished the sp cache update')

if __name__ == '__main__':
    script = PackageCacheUpdater('spcache', dbuser=config.statistician.dbuser)
    script.lock_and_run()

