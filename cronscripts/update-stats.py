#!/usr/bin/python2.4
# Copyright 2004 Canonical Ltd.  All rights reserved.

# This script updates the cached stats in the system

import _pythonpath

from zope.component import getUtility
from canonical.lp import READ_COMMITTED_ISOLATION
from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.interfaces import (
    IDistributionSet, ILaunchpadStatisticSet, IPersonSet
    )
from canonical.config import config


class StatUpdater(LaunchpadCronScript):
    def main(self):
        self.txn.set_isolation_level(READ_COMMITTED_ISOLATION)

        self.logger.debug('Starting the stats update')

        # Note that we do not issue commits here in the script; content
        # objects are responsible for committing.
        distroset = getUtility(IDistributionSet)
        for distro in distroset:
            for distroseries in distro.serieses:
                distroseries.updateStatistics(self.txn)

        launchpad_stats = getUtility(ILaunchpadStatisticSet)
        launchpad_stats.updateStatistics(self.txn)

        getUtility(IPersonSet).updateStatistics(self.txn)

        self.logger.debug('Finished the stats update')


if __name__ == '__main__':
    script = StatUpdater('launchpad-stats',
                         dbuser=config.statistician.dbuser)
    script.lock_and_run()

