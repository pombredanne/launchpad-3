#!/usr/bin/env python
"""
Cron job to run daily to check all of the BugWatches
"""

# Stick launchpad/lib in the PYTHONPATH to make running this script easier
import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, 'lib'))

import logging
from optparse import OptionParser

from canonical.lp import initZopeless
from canonical.database.constants import UTC_NOW
from canonical.launchpad.database.bugwatch import BugWatch
from canonical.launchpad.database.bugtracker import BugTracker
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.malone import externalsystem

_default_lock_file = '/var/lock/launchpad-checkwatches.lock'

versioncache = {}

def parse_options():
    parser = OptionParser()
    parser.add_option("-v", "--verbose", dest="verbose",
        default=0, action="count",
        help="Displays extra information.")
    parser.add_option("-q", "--quiet", dest="quiet",
        default=0, action="count",
        help="Display less information.")
    parser.add_option("-l", "--lockfile", dest="lockfilename",
        default=_default_lock_file,
        help="The file the script should use to lock the process.")

    (options, args) = parser.parse_args()

    return options

def setUpLogger():
    loglevel = logging.WARN

    verbosity = options.verbose - options.quiet
    if verbosity > 2:
        verbosity = 2
    elif verbosity < -2:
        verbosity = -2

    loglevel = {
        -2: logging.CRITICAL,
        -1: logging.ERROR,
        0: logging.WARN,
        1: logging.INFO,
        2: logging.DEBUG,
        }[verbosity]

    hdlr = logging.StreamHandler(strm=sys.stderr)
    hdlr.setFormatter(logging.Formatter(
        fmt='%(asctime)s %(levelname)s %(message)s'
        ))
    logger.addHandler(hdlr)
    logger.setLevel(loglevel)


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
        remotesystem = externalsystem.ExternalSystem(bugtracker,version)
    except externalsystem.UnknownBugTrackerTypeError, val:
        logger.error("BugTrackerType '%s' is not known", val.bugtrackertypename)
    except externalsystem.BugTrackerConnectError:
        logger.exepption("Got error trying to contact %s", bugtracker.name)
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
    logger = logging.getLogger("checkwatches")
    setUpLogger()
    lockfile = LockFile(options.lockfilename, logger=logger)
    try:
        lockfile.acquire()
    except OSError:
        pass
    else:
        try:
            main()
        finally:
            lockfile.release()

