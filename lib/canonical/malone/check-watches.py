#!/usr/bin/env python
"""
Cron job to run daily to check all of the BugWatches
"""

from sqlobject import connectionForURI
from canonical.arch.sqlbase import SQLBase, quote
from canonical.database.malone import BugWatch, BugSystem
import sqlobject, externalsystem

# This script probably doesn't work yet, it'll get cleaned up
# after I get it tagged over to my desktop machine again. --dave

def check_one_watch(watch):
    bugsystem = watch.bugsystem
    try:
        remotesystem = ExternalSystem(bugsystem)
    except UnkownBugSystemTypeError, val:
        print "*** WARNING: Bugsystem Type '%s' is not known" % (
            val.bugsystemtypename, )
        print "    Skipping %s bug %s watch on bug %s" % (
            val.bugsystemname, watch.remotebug, watch.bug)
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
