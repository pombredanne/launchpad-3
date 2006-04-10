#!/usr/bin/env python
"""
Cron job to run daily to check all of the BugWatches
"""

import sys
import _pythonpath

from optparse import OptionParser

from zope.component import getUtility

from canonical.lp import initZopeless
from canonical.launchpad.interfaces import (
    IBugTrackerSet, ILaunchpadCelebrities)
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.launchpad.components import externalbugtracker
from canonical.launchpad import scripts

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

    for bug_tracker in getUtility(IBugTrackerSet):
        if bug_tracker == ubuntu_bugzilla:
            # No need updating Ubuntu Bugzilla watches since all bugs
            # have been imported into Malone, and thus won't change.
            log.info("Skipping updating Ubuntu Bugzilla watches.")
            continue
        # We want 1 day, but we'll use 23 hours because we can't count
        # on the cron job hitting exactly the same time every day
        bug_watches_to_update = bug_tracker.getBugWatchesNeedingUpdate(23)

        try:
            remotesystem = externalbugtracker.get_external_bugtracker(
                bug_tracker)
        except externalbugtracker.UnknownBugTrackerTypeError, error:
            log.info(
                "ExternalBugtracker for BugTrackerType '%s' is not known.",
                error.bugtrackertypename)
        else:
            number_of_watches = bug_watches_to_update.count()
            if number_of_watches > 0:
                log.info(
                    "Updating %i watches on %s" % (
                        number_of_watches, bug_tracker.baseurl))
                try:
                    remotesystem.updateBugWatches(bug_watches_to_update)
                except externalbugtracker.BugTrackerConnectError:
                    log.exception(
                        "Got error trying to contact %s", bug_tracker.name)
                except externalbugtracker.UnsupportedBugTrackerVersion, error:
                    log.warning(str(error))
                else:
                    txn.commit()
            else:
                log.info("No watches to update on %s" % bug_tracker.baseurl)


if __name__ == '__main__':
    options = parse_options()
    log = scripts.logger(options, "checkwatches")
    lockfile = LockFile(options.lockfilename, logger=log)
    try:
        lockfile.acquire()
    except OSError:
        log.info('Lockfile %s in use' % options.lockfilename)
        sys.exit(1)
    try:
        main()
    finally:
        lockfile.release()

