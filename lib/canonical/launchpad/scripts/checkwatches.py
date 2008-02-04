# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Helper functions for the checkwatches.py cronscript."""

__metaclass__ = type


from logging import getLogger
import socket

from zope.component import getUtility

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import commit
from canonical.launchpad.components import externalbugtracker
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, IBugTrackerSet)
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
from canonical.launchpad.webapp.interaction import (
    setupInteraction, endInteraction)


class BugWatchUpdater(object):
    """Takes responsibility for updating remote bug watches."""

    def __init__(self, txn, log=None):
        if log is None:
            self.log = getLogger()
        else:
            self.log = log

        self.txn = txn

    def _login(self):
        """Set up an interaction as the Bug Watch Updater"""
        auth_utility = getUtility(IPlacelessAuthUtility)
        setupInteraction(
            auth_utility.getPrincipalByLogin('bugwatch@bugs.launchpad.net'),
            login='bugwatch@bugs.launchpad.net')

    def _logout(self):
        """Tear down the Bug Watch Updater Interaction."""
        endInteraction()

    def updateBugTrackers(self, bug_tracker_names=None):
        """Update all the bug trackers that have watches pending.

        If bug tracker names are specified in bug_tracker_names only
        those bug trackers will be checked.
        """
        ubuntu_bugzilla = getUtility(ILaunchpadCelebrities).ubuntu_bugzilla

        # Set up an interaction as the Bug Watch Updater since the
        # notification code expects a logged in user.
        self._login()

        bug_tracker_set = getUtility(IBugTrackerSet)
        for bug_tracker in bug_tracker_set:
            # If a set of bug tracker names to check has been specified
            # we discard those bug trackers whose names don't appear in
            # that set.
            if (bug_tracker_names is not None and
                bug_tracker.name not in bug_tracker_names):
                continue

            self.txn.begin()
            # Save the url for later, since we might need it to report an
            # error after a transaction has been aborted.
            bug_tracker_url = bug_tracker.baseurl
            try:
                if bug_tracker == ubuntu_bugzilla:
                    # XXX: 2007-09-11 Graham Binns
                    #      We automatically ignore the Ubuntu Bugzilla
                    #      here as all its bugs have been imported into
                    #      Launchpad. Ideally we would have some means
                    #      to identify all bug trackers like this so
                    #      that hard-coding like this can be genericised
                    #      (Bug 138949).
                    self.log.info(
                        "Skipping updating Ubuntu Bugzilla watches.")
                else:
                    self.updateBugTracker(bug_tracker)

                # XXX 2008-01-22 gmb:
                #     We should be using self.txn.commit() here, however
                #     there's a known issue with ztm.commit() in that it
                #     only works once per Zopeless script run (bug
                #     3989). Using commit() directly is the best
                #     available workaround, but we need to change this
                #     once the bug is resolved.
                commit()
            except (KeyboardInterrupt, SystemExit):
                # We should never catch KeyboardInterrupt or SystemExit.
                raise
            except:
                # If something unexpected goes wrong, we log it and
                # continue: a failure shouldn't break the updating of
                # the other bug trackers.
                self.log.error(
                    "An exception was raised when updating %s" %
                    bug_tracker_url,
                    exc_info=True)
                self.txn.abort()
        self._logout()

    def _getExternalBugTracker(self, bug_tracker):
        """Return an `ExternalBugTracker` instance for `bug_tracker`."""
        return externalbugtracker.get_external_bugtracker(
            self.txn, bug_tracker)

    def updateBugTracker(self, bug_tracker):
        """Updates the given bug trackers's bug watches."""
        # XXX 2007-01-18 gmb:
        #     Once we start running checkwatches more frequently we need
        #     to update the comment and the call to
        #     getBugWatchesNeedingUpdate() below. We'll be checking
        #     those watches which haven't been checked for 24 hours, not
        #     23.
        # We want 1 day, but we'll use 23 hours because we can't count
        # on the cron job hitting exactly the same time every day
        bug_watches_to_update = (
            bug_tracker.getBugWatchesNeedingUpdate(23))

        try:
            remotesystem = self._getExternalBugTracker(bug_tracker)
        except externalbugtracker.UnknownBugTrackerTypeError, error:
            # We update all the bug watches to reflect the fact that
            # this error occurred. We also update their last checked
            # date to ensure that they don't get checked for another
            # 24 hours (see above).
            error_type = (
                externalbugtracker.get_bugwatcherrortype_for_error(error))
            for bug_watch in bug_watches_to_update:
                bug_watch.last_error_type = error_type
                bug_watch.lastchecked = UTC_NOW

            self.log.info(
                "ExternalBugtracker for BugTrackerType '%s' is not "
                "known." % (error.bugtrackertypename))
        else:
            if bug_watches_to_update.count() > 0:
                try:
                    remotesystem.updateBugWatches(bug_watches_to_update)
                except externalbugtracker.BugWatchUpdateError, error:
                    self.log.error(str(error))
                except socket.timeout:
                    # We don't want to die on a timeout, since most likely
                    # it's just a problem for this iteration. Nevertheless
                    # we log the problem.
                    self.log.error(
                        "Connection timed out when updating %s" %
                        bug_tracker.baseurl)
                    self.txn.abort()
            else:
                self.log.info(
                    "No watches to update on %s" % bug_tracker.baseurl)

