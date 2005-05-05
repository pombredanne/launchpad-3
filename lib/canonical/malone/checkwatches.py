#!/usr/bin/env python
"""
Cron job to run daily to check all of the BugWatches
"""

# Stick launchpad/lib in the PYTHONPATH to make running this script easier
import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))

from canonical.lp import initZopeless
from canonical.database.constants import UTC_NOW
from canonical.launchpad.database.bugwatch import BugWatch
from canonical.launchpad.database.bugtracker import BugTracker
from canonical.database.sqlbase import SQLBase
import sqlobject, externalsystem

versioncache = {}

def check_one_watch(watch):
    bugtracker = watch.bugtracker
    if versioncache.has_key(bugtracker.baseurl):
        version = versioncache[bugtracker.baseurl]
    else:
        version = None
    print "Checking: %s %s for bug %d" % (
            bugtracker.name, watch.remotebug, watch.bug.id
            )
    watch.lastchecked = UTC_NOW
    try:
        remotesystem = externalsystem.ExternalSystem(bugtracker,version)
    except externalsystem.UnknownBugTrackerTypeError, val:
        # TODO: Raise an error on UnknownBugTrackerType. Currently
        # not even warning to stop cron spam -- StuartBishop 20050505
        pass
        #print "*** WARNING: BugTrackerType '%s' is not known" % (
        #    val.bugtrackertypename, )
        #print "    Skipping %s bug %s watch on bug %s" % (
        #    val.bugtrackername, watch.remotebug, watch.bug)
    except externalsystem.BugTrackerConnectError, val:
        print "*** WARNING: Got error trying to contact %s" % bugtracker.name
        print "    %s" % val
    else:
        versioncache.update({ bugtracker.baseurl : remotesystem.version })
        remotestatus = remotesystem.get_bug_status(watch.remotebug)
        if remotestatus != watch.remotestatus:
            print "it's changed - updating"
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
    main()

