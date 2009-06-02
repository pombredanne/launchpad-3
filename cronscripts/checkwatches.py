#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

"""
Cron job to run daily to check all of the BugWatches
"""

import time
import _pythonpath

from canonical.config import config
from lp.services.scripts.base import LaunchpadCronScript
from canonical.launchpad.scripts.checkwatches import BugWatchUpdater


class CheckWatches(LaunchpadCronScript):

    def add_my_options(self):
        """See `LaunchpadScript`."""
        self.parser.add_option(
            '-t', '--bug-tracker', action='append',
            dest='bug_trackers', metavar="BUG_TRACKER",
            help="Only check a given bug tracker. Specifying more than "
                "one bugtracker using this option will check all the "
                "bugtrackers specified.")
        self.parser.add_option(
            '-b', '--batch-size', action='store', dest='batch_size',
            help="Set the number of watches to be checked per bug "
                 "tracker in this run. If BATCH_SIZE is 0, all watches "
                 "on the bug tracker that are eligible for checking will "
                 "be checked.")

    def main(self):
        start_time = time.time()

        updater = BugWatchUpdater(self.txn, self.logger)

        # Make sure batch_size is an integer or None.
        batch_size = self.options.batch_size
        if batch_size is not None:
            batch_size = int(batch_size)

        updater.updateBugTrackers(self.options.bug_trackers, batch_size)

        run_time = time.time() - start_time
        self.logger.info("Time for this run: %.3f seconds." % run_time)


if __name__ == '__main__':
    script = CheckWatches("checkwatches", dbuser=config.checkwatches.dbuser)
    script.lock_and_run()
