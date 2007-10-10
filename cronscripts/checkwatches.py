#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

"""
Cron job to run daily to check all of the BugWatches
"""

import socket
import time
import _pythonpath

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.scripts.checkwatches import BugWatchUpdater

class CheckWatches(LaunchpadCronScript):
    def main(self):
        start_time = time.time()

        updater = BugWatchUpdater(self.txn, self.logger)
        updater.updateBugTrackers()

        run_time = time.time() - start_time
        self.logger.info("Time for this run: %.3f seconds." %
            run_time)

if __name__ == '__main__':
    script = CheckWatches("checkwatches")
    script.lock_and_run()

