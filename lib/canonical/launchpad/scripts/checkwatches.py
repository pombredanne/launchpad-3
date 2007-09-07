# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Helper functions for the checkwatches.py cronscript."""

__metaclass__ = type


from logging import getLogger

from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import cursor, sqlvalues
from canonical.launchpad.components import externalbugtracker
from canonical.launchpad.interfaces import ILaunchpadCelebrities, IQuestionSet
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
from canonical.launchpad.webapp.interaction import (
    setupInteraction, endInteraction)


class BugWatchUpdate(object):
    """Takes responsibility for updating remote bug watches."""

    def __init__(self):
        pass

    def _login(self):
        """Set up an interaction as the Bug Watch Updater"""
        auth_utility = getUtility(IPlacelessAuthUtility)
        setupInteraction(
            auth_utility.getPrincipalByLogin('bugwatch@bugs.launchpad.net'),
            login='bugwatch@bugs.launchpad.net')

    def _logout(self):
        """Removed the Support Tracker Janitor interaction."""
        endInteraction()

    def updateBugTracker(bug_tracker, log):
        """Updates the given bug trackers's bug watches."""
        # We want 1 day, but we'll use 23 hours because we can't count
        # on the cron job hitting exactly the same time every day
        bug_watches_to_update = bug_tracker.getBugWatchesNeedingUpdate(23)

        try:
            remotesystem = externalbugtracker.get_external_bugtracker(
                bug_tracker)
        except externalbugtracker.UnknownBugTrackerTypeError, error:
            log.info(
                "ExternalBugtracker for BugTrackerType '%s' is not"
                "known." % (
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

