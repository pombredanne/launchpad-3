#!/usr/bin/env python
"""
Cron job to run daily to check all of the BugWatches
"""

from canonical.launchpad.database import BugWatch, BugTracker
from externalsystem import ExternalSystem

# This script probably doesn't work yet, it'll get cleaned up
# after I get it tagged over to my desktop machine again. --dave

def check_one_watch(watch):
    bugtracker = watch.bugtracker
    try:
        remotesystem = ExternalSystem(bugtracker)
    # XXX this name doesn't exist anywhere
    except UnknownBugTrackerTypeError, val:
        print "*** WARNING: BugTrackerType '%s' is not known" % (
            val.bugtrackertypename, )
        print "    Skipping %s bug %s watch on bug %s" % (
            val.bugtrackername, watch.remotebug, watch.bug)
    else:
        remotestatus = remotesystem.get_bug_status(watch.remotebug)
        if remotestatus != watch.remotestatus:
            watch.remotestatus = remotestatus
            watch.lastchanged = now #### XXX - FIX THIS ####
        watch.lastchecked = now #### XXX - FIX THIS ####
    

def main():
    ### TODO - need to look up SQL for postgres; this is probably
    #          mysql dialect
    watches = BugWatch.select("(lastchecked > interval 1 days)")
    for watch in watches:
        check_one_watch(watch)

if __name__ == '__main__':
    main()

# arch-tag: fc5ed49f-b515-440c-8fdb-ae38ce3b8a7f
