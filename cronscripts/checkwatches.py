#!/usr/bin/env python
"""
Cron job to run daily to check all of the BugWatches
"""

import sys
import _pythonpath

from optparse import OptionParser

from canonical.lp import initZopeless
from canonical.database.constants import UTC_NOW
from canonical.launchpad.database.bugwatch import BugWatch
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.malone import externalsystem
from canonical.launchpad.scripts import logger, logger_options

_default_lock_file = '/var/lock/launchpad-checkwatches.lock'

versioncache = {}

def parse_options():
    parser = OptionParser()
    logger_options(parser)
    parser.add_option("-l", "--lockfile", dest="lockfilename",
        default=_default_lock_file,
        help="The file the script should use to lock the process.")

    (options, args) = parser.parse_args()

    return options


def check_one_watch(watch):
    bugtracker = watch.bugtracker
    if versioncache.has_key(bugtracker.baseurl):
        version = versioncache[bugtracker.baseurl]
    else:
        version = None
    logger.info(
            "Checking: %s %s for bug %d",
            bugtracker.name, watch.remotebug, watch.bug.id
            )
    watch.lastchecked = UTC_NOW
    try:
        remotesystem = externalsystem.ExternalSystem(bugtracker, version)
    except externalsystem.UnknownBugTrackerTypeError, val:
        if val == 'debbugs':
            pass # Yes, we know. Just stop spamming us
        else:
            logger.error("BugTrackerType '%s' is not known",
                    val.bugtrackertypename)
    except externalsystem.BugTrackerConnectError:
        logger.exception("Got error trying to contact %s", bugtracker.name)
    else:
        versioncache.update({ bugtracker.baseurl : remotesystem.version })
        remotestatus = remotesystem.get_bug_status(watch.remotebug)
        if remotestatus != watch.remotestatus:
            logger.debug("it's changed - updating")
            if remotestatus == None:
                remotestatus = 'UNKNOWN'
            watch.remotestatus = remotestatus
        watch.lastchanged = UTC_NOW


def main():
    txn = initZopeless()
    # We want 1 day, but we'll use 23 hours because we can't count on the cron
    # job hitting exactly the same time every day
    watches = BugWatch.select(
        """(lastchecked < (now() at time zone 'UTC' - interval '23 hours') OR
          lastchecked IS NULL)""")
    for watch in watches:
        check_one_watch(watch)
        txn.commit()


if __name__ == '__main__':
    options = parse_options()
    my_logger = logger(options, "checkwatches")
    lockfile = LockFile(options.lockfilename, logger=my_logger)
    try:
        lockfile.acquire()
    except OSError:
        my_logger.info('Lockfile %s in use' % options.lockfilename)
        sys.exit(1)
    try:
        main()
    finally:
        lockfile.release()

