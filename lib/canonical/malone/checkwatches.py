#!/usr/bin/env python
"""
Cron job to run daily to check all of the BugWatches
"""

# Stick launchpad/lib in the PYTHONPATH to make running this script easier
import sys, os.path
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))

from canonical.lp import initZopeless
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
    print "Checking: %s %s for bug %d" % (bugtracker.name,
        watch.remotebug, watch.bug.id)
    try:
        remotesystem = externalsystem.ExternalSystem(bugtracker,version)
    # XXX this name doesn't exist anywhere
    except externalsystem.UnknownBugTrackerTypeError, val:
        print "*** WARNING: BugTrackerType '%s' is not known" % (
            val.bugtrackertypename, )
        print "    Skipping %s bug %s watch on bug %s" % (
            val.bugtrackername, watch.remotebug, watch.bug)
        return
    except externalsystem.BugTrackerConnectError, val:
        print "*** WARNING: Got error trying to contact %s" % bugtracker.name
        print "    %s" % val
        return
    else:
        versioncache.update({ bugtracker.baseurl : remotesystem.version })
        remotestatus = remotesystem.get_bug_status(watch.remotebug)
        if remotestatus != watch.remotestatus:
            print "it's changed - updating"
            if remotestatus == None:
                remotestatus = 'UNKNOWN'
            watch.remotestatus = remotestatus
            watch.lastchanged = 'NOW'
        watch.lastchecked = 'NOW'

def main():
    initZopeless()

    # We want 1 day, but we'll use 23 hours because we can't count on the cron
    # job hitting exactly the same time every day
    watches = BugWatch.select(
        "(lastchecked < (now() at time zone 'UTC' - interval '23 hours'))")
    for watch in watches:
        check_one_watch(watch)

if __name__ == '__main__':
    main()

