#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

"""
Cron job to run daily to check all of the BugWatches
"""

import time
import _pythonpath

from canonical.config import config
from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.scripts.checkwatches import BugWatchUpdater


class CheckWatches(LaunchpadCronScript):
    def main(self):
        start_time = time.time()

        errorreports_config = config.launchpad.errorreports

        # Save current OOPS configuration settings.
        current_oops_prefix = errorreports_config.oops_prefix
        current_copy_to_zlog = errorreports_config.copy_to_zlog
        try:
            # checkwatches has been assigned the prefix 'CW.
            errorreports_config.oops_prefix += '-CW'
            # Don't copy OOPSes to the zlog; we will do that
            # explicitely. See `externalbugtracker.report_oops` and
            # `report_warning`.
            errorreports_config.copy_to_zlog = False

            updater = BugWatchUpdater(self.txn, self.logger)
            updater.updateBugTrackers()

        finally:
            # Restore previous configuration settings.
            errorreports_config.oops_prefix = current_oops_prefix
            errorreports_config.copy_to_zlog = current_copy_to_zlog

        run_time = time.time() - start_time
        self.logger.info("Time for this run: %.3f seconds." % run_time)


if __name__ == '__main__':
    script = CheckWatches("checkwatches", dbuser=config.checkwatches.dbuser)
    script.lock_and_run()
