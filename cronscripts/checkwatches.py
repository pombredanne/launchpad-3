#!/usr/bin/env python
"""
Cron job to run daily to check all of the BugWatches
"""

import sys
import _pythonpath

from optparse import OptionParser

from contrib.glock import GlobalLock, GlobalLockError

from zope.component import getUtility

from canonical.lp import initZopeless
from canonical.launchpad.interfaces import (
    IBugTrackerSet, ILaunchpadCelebrities)
from canonical.launchpad.scripts.checkwatches import update_bug_tracker
from canonical.launchpad import scripts
from canonical.launchpad.ftests import login

_default_lock_file = '/var/lock/launchpad-checkwatches.lock'


def parse_options():
    parser = OptionParser()
    scripts.logger_options(parser)
    parser.add_option("-l", "--lockfile", dest="lockfilename",
        default=_default_lock_file,
        help="The file the script should use to lock the process.")

    (options, args) = parser.parse_args()

    return options


def main():
    txn = initZopeless()
    scripts.execute_zcml_for_scripts()
    ubuntu_bugzilla = getUtility(ILaunchpadCelebrities).ubuntu_bugzilla

    # Set up an interaction as the Bug Watch Updater since the
    # notification code expects a logged in user.
    login('bugwatch@bugs.launchpad.net')

    for bug_tracker in getUtility(IBugTrackerSet):
        txn.begin()
        # Save the url for later, since we might need it to report an
        # error after a transaction has been aborted.
        bug_tracker_url = bug_tracker.baseurl
        try:
            if bug_tracker == ubuntu_bugzilla:
                # No need updating Ubuntu Bugzilla watches since all bugs
                # have been imported into Malone, and thus won't change.
                log.info("Skipping updating Ubuntu Bugzilla watches.")
            else:
                update_bug_tracker(bug_tracker, log)
            txn.commit()
        except (KeyboardInterrupt, SystemExit):
            # We should never catch KeyboardInterrupt or SystemExit.
            raise
        except:
            # If something unexpected goes wrong, we shouldn't break the
            # updating of the other bug trackers.
            log.error(
                "An exception was raised when updating %s" % bug_tracker_url,
                exc_info=True)
            txn.abort()


if __name__ == '__main__':
    options = parse_options()
    log = scripts.logger(options, "checkwatches")
    lockfile = GlobalLock(options.lockfilename, logger=log)
    try:
        lockfile.acquire()
    except GlobalLockError:
        log.error('Lockfile %s in use' % options.lockfilename)
        sys.exit(1)
    try:
        main()
    finally:
        lockfile.release()

