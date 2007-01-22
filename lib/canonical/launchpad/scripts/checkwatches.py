# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Helper functions for the checkwatches.py cronscript."""

__metaclass__ = type


from canonical.launchpad.components import externalbugtracker


def update_bug_tracker(bug_tracker, log):
    """Updates the given bug trackers's bug watches."""
    # We want 1 day, but we'll use 23 hours because we can't count
    # on the cron job hitting exactly the same time every day
    bug_watches_to_update = bug_tracker.getBugWatchesNeedingUpdate(23)

    try:
        remotesystem = externalbugtracker.get_external_bugtracker(bug_tracker)
    except externalbugtracker.UnknownBugTrackerTypeError, error:
        log.info(
            "ExternalBugtracker for BugTrackerType '%s' is not known." % (
                error.bugtrackertypename))
    else:
        number_of_watches = bug_watches_to_update.count()
        if number_of_watches > 0:
            log.info(
                "Updating %i watches on %s" % (
                    number_of_watches, bug_tracker.baseurl))
            try:
                remotesystem.updateBugWatches(bug_watches_to_update)
            except externalbugtracker.BugWatchUpdateError, error:
                log.error(str(error))
        else:
            log.info("No watches to update on %s" % bug_tracker.baseurl)
