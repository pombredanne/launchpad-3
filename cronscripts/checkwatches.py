#!/usr/bin/python2.4
"""
Cron job to run daily to check all of the BugWatches
"""

import _pythonpath

from zope.component import getUtility

from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.scripts.checkwatches import update_bug_tracker
from canonical.launchpad.interfaces import (
    IBugTrackerSet, ILaunchpadCelebrities)

class CheckWatches(LaunchpadCronScript):
    def main(self):
        ubuntu_bugzilla = getUtility(ILaunchpadCelebrities).ubuntu_bugzilla

        # Set up an interaction as the Bug Watch Updater since the
        # notification code expects a logged in user.
        self.login('bugwatch@bugs.launchpad.net')

        for bug_tracker in getUtility(IBugTrackerSet):
            self.txn.begin()
            # Save the url for later, since we might need it to report an
            # error after a transaction has been aborted.
            bug_tracker_url = bug_tracker.baseurl
            try:
                if bug_tracker == ubuntu_bugzilla:
                    # No need updating Ubuntu Bugzilla watches since all bugs
                    # have been imported into Malone, and thus won't change.
                    self.logger.info("Skipping updating Ubuntu Bugzilla watches.")
                else:
                    update_bug_tracker(bug_tracker, self.logger)
                self.txn.commit()
            except (KeyboardInterrupt, SystemExit):
                # We should never catch KeyboardInterrupt or SystemExit.
                raise
            except:
                # If something unexpected goes wrong, we log it and
                # continue: a failure shouldn't break the updating of
                # the other bug trackers.
                self.logger.error(
                    "An exception was raised when updating %s" % bug_tracker_url,
                    exc_info=True)
                self.txn.abort()

if __name__ == '__main__':
    script = CheckWatches("checkwatches")
    script.lock_and_run()

