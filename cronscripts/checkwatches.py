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

    def add_my_options(self):
        """See `LaunchpadScript`."""
        self.parser.add_option('-t', '--bug-tracker', action='append',
            dest='bug_trackers', metavar="BUG_TRACKER",
            help="Only check a given bug tracker. Specifying more than "
                "one bugtracker using this option will check all the "
                "bugtrackers specified.")

    def main(self):
        start_time = time.time()

        updater = BugWatchUpdater(self.txn, self.logger)
        updater.updateBugTrackers(self.options.bug_trackers)

        run_time = time.time() - start_time
        self.logger.info("Time for this run: %.3f seconds." % run_time)


if __name__ == '__main__':
    script = CheckWatches("checkwatches", dbuser=config.checkwatches.dbuser)
    script.lock_and_run()
