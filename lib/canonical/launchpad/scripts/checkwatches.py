# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Helper functions for the checkwatches.py cronscript."""

__metaclass__ = type


from logging import getLogger
import socket
import sys

from zope.component import getUtility

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import commit, flush_database_updates
from canonical.launchpad.components import externalbugtracker
from canonical.launchpad.components.externalbugtracker import (
    BugNotFound, BugTrackerConnectError, InvalidBugId, UnparseableBugData,
    UnparseableBugTrackerVersion, UnsupportedBugTrackerVersion,
    UnknownBugTrackerTypeError)
from canonical.launchpad.interfaces import (
    BugWatchErrorType, CreateBugParams, IBugTrackerSet, IBugWatchSet,
    IDistribution, ILaunchpadCelebrities, IPersonSet, ISupportsCommentImport,
    PersonCreationRationale)
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
from canonical.launchpad.webapp.interaction import (
    setupInteraction, endInteraction)


_exception_to_bugwatcherrortype = [
   (BugTrackerConnectError, BugWatchErrorType.CONNECTION_ERROR),
   (UnparseableBugData, BugWatchErrorType.UNPARSABLE_BUG),
   (UnparseableBugTrackerVersion, BugWatchErrorType.UNPARSABLE_BUG_TRACKER),
   (UnsupportedBugTrackerVersion, BugWatchErrorType.UNSUPPORTED_BUG_TRACKER),
   (UnknownBugTrackerTypeError, BugWatchErrorType.UNSUPPORTED_BUG_TRACKER),
   (socket.timeout, BugWatchErrorType.TIMEOUT)]


def get_bugwatcherrortype_for_error(error):
    """Return the correct `BugWatchErrorType` for a given error."""
    for exc_type, bugwatcherrortype in _exception_to_bugwatcherrortype:
        if isinstance(error, exc_type):
            return bugwatcherrortype
    else:
        return BugWatchErrorType.UNKNOWN


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
                info = sys.exc_info()
                externalbugtracker.report_oops(
                    info=info, properties=[
                        ('bugtracker', bug_tracker.name),
                        ('baseurl', bug_tracker_url)])
                self.log.error(
                    "An exception was raised when updating %s" %
                    bug_tracker_url, exc_info=info)
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

            message = (
                "ExternalBugtracker for BugTrackerType '%s' is not known." % (
                    error.bugtrackertypename))
            externalbugtracker.report_warning(message)
            self.log.warning(message)
        else:
            if bug_watches_to_update.count() > 0:
                try:
                    self.updateBugWatches(remotesystem, bug_watches_to_update)
                except externalbugtracker.BugWatchUpdateError, error:
                    externalbugtracker.report_oops(
                        properties=[
                            ('bugtracker', bug_tracker.name),
                            ('baseurl', bug_tracker.baseurl)])
                    self.log.error(str(error))
                    self.txn.abort()
                except socket.timeout:
                    # We don't want to die on a timeout, since most likely
                    # it's just a problem for this iteration. Nevertheless
                    # we log the problem.
                    externalbugtracker.report_oops(
                        properties=[
                            ('bugtracker', bug_tracker.name),
                            ('baseurl', bug_tracker.baseurl)])
                    self.log.error(
                        "Connection timed out when updating %s" % (
                            bug_tracker.baseurl))
                    self.txn.abort()
            else:
                self.log.info(
                    "No watches to update on %s" % bug_tracker.baseurl)

    def updateBugWatches(self, remotesystem, bug_watches_to_update):
        """Update the given bug watches."""
        # Save the url for later, since we might need it to report an
        # error after a transaction has been aborted.
        bug_tracker_url = remotesystem.baseurl

        # Some tests pass a list of bug watches whilst checkwatches.py
        # will pass a SelectResults instance. We convert bug_watches to a
        # list here to ensure that were're doing sane things with it
        # later on.
        bug_watches = list(bug_watches_to_update)

        # We limit the number of watches we're updating by the
        # ExternalBugTracker's batch_size. In an ideal world we'd just
        # slice the bug_watches list but for the sake of testing we need
        # to ensure that the list of bug watches is ordered by remote
        # bug id before we do so.
        remote_ids = sorted(
            [bug_watch.remotebug for bug_watch in bug_watches])
        if remotesystem.batch_size is not None:
            remote_ids = remote_ids[:remotesystem.batch_size]

            for bug_watch in list(bug_watches):
                if bug_watch.remotebug not in remote_ids:
                    bug_watches.remove(bug_watch)

        remotesystem.info("Updating %i watches on %s" %
            (len(bug_watches), bug_tracker_url))

        bug_watch_ids = [bug_watch.id for bug_watch in bug_watches]
        bug_watches_by_remote_bug = remotesystem._getBugWatchesByRemoteBug(
            bug_watch_ids)

        # Do things in a fixed order, mainly to help with testing.
        bug_ids_to_update = sorted(bug_watches_by_remote_bug)

        try:
            remotesystem.initializeRemoteBugDB(bug_ids_to_update)
        except Exception, error:
            # We record the error against all the bugwatches that should
            # have been updated before re-raising it. We also update the
            # bug watches' lastchecked dates so that checkwatches
            # doesn't keep trying to update them every time it runs.
            errortype = get_bugwatcherrortype_for_error(error)
            for bugwatch in bug_watches:
                bugwatch.lastchecked = UTC_NOW
                bugwatch.last_error_type = errortype
            raise

        # Again, fixed order here to help with testing.
        bug_ids = sorted(bug_watches_by_remote_bug.keys())
        for bug_id in bug_ids:
            bug_watches = bug_watches_by_remote_bug[bug_id]
            local_ids = ", ".join(str(watch.bug.id) for watch in bug_watches)
            try:
                new_remote_status = None
                new_malone_status = None
                new_remote_importance = None
                new_malone_importance = None
                error = None

                # XXX: 2007-10-17 Graham Binns
                #      This nested set of try:excepts isn't really
                #      necessary and can be refactored out when bug
                #      136391 is dealt with.
                try:
                    new_remote_status = remotesystem.getRemoteStatus(bug_id)
                    new_malone_status = remotesystem.convertRemoteStatus(
                        new_remote_status)

                    new_remote_importance = remotesystem.getRemoteImportance(
                        bug_id)
                    new_malone_importance = (
                        remotesystem.convertRemoteImportance(
                            new_remote_importance))
                except InvalidBugId:
                    error = BugWatchErrorType.INVALID_BUG_ID
                    remotesystem.warning(
                        "Invalid bug %r on %s (local bugs: %s)." %
                             (bug_id, remotesystem.baseurl, local_ids),
                        properties=[
                            ('bug_id', bug_id),
                            ('local_ids', local_ids)],
                        info=sys.exc_info())
                except BugNotFound:
                    error = BugWatchErrorType.BUG_NOT_FOUND
                    remotesystem.warning(
                        "Didn't find bug %r on %s (local bugs: %s)." %
                             (bug_id, remotesystem.baseurl, local_ids),
                        properties=[
                            ('bug_id', bug_id),
                            ('local_ids', local_ids)],
                        info=sys.exc_info())

                for bug_watch in bug_watches:
                    bug_watch.lastchecked = UTC_NOW
                    bug_watch.last_error_type = error
                    if new_malone_status is not None:
                        bug_watch.updateStatus(new_remote_status,
                            new_malone_status)
                    if new_malone_importance is not None:
                        bug_watch.updateImportance(new_remote_importance,
                            new_malone_importance)
                    if (ISupportsCommentImport.providedBy(remotesystem) and
                        remotesystem.import_comments):
                        remotesystem.importBugComments(bug_watch)

            except (KeyboardInterrupt, SystemExit):
                # We should never catch KeyboardInterrupt or SystemExit.
                raise
            except Exception, error:
                # If something unexpected goes wrong, we shouldn't break the
                # updating of the other bugs.

                # Restart the transaction so that subsequent
                # bug watches will get recorded.
                self.txn.abort()
                self.txn.begin()
                bug_watches_by_remote_bug = (
                    remotesystem._getBugWatchesByRemoteBug(
                        bug_watch_ids))

                # We record errors against the bug watches and update
                # their lastchecked dates so that we don't try to
                # re-check them every time checkwatches runs.
                errortype = get_bugwatcherrortype_for_error(error)
                for bugwatch in bug_watches:
                    bugwatch.lastchecked = UTC_NOW
                    bugwatch.last_error_type = errortype

                remotesystem.error(
                    "Failure updating bug %r on %s (local bugs: %s)." %
                            (bug_id, bug_tracker_url, local_ids),
                    properties=[
                        ('bug_id', bug_id),
                        ('local_ids', local_ids)])

    def importBug(self, external_bugtracker, bugtracker, bug_target,
                  remote_bug):
        """Import a remote bug into Launchpad.

        :param external_bugtracker: An ISupportsBugImport, which talks
            to the external bug tracker.
        :param bugtracker: An IBugTracker, to which the created bug
            watch will be linked. 
        :param bug_target: An IBugTarget, to which the created bug will
            be linked.
        :param remote_bug: The remote bug id as a string.

        :return: The created Launchpad bug.
        """
        assert IDistribution.providedBy(bug_target), (
            'Only imports of bugs for a distribution is implemented.')
        reporter_name, reporter_email = external_bugtracker.getBugReporter(
            remote_bug)
        reporter = getUtility(IPersonSet).ensurePerson(
            reporter_email, reporter_name, PersonCreationRationale.BUGIMPORT,
            comment='when importing bug #%s from %s' % (
                remote_bug, external_bugtracker.baseurl))
        package_name = external_bugtracker.getBugTargetName(remote_bug)
        package = bug_target.getSourcePackage(package_name)
        if package is not None:
            bug_target = package
        else:
            external_bugtracker.warning(
                'Unknown %s package (#%s at %s): %s' % (
                    bug_target.name, remote_bug,
                    external_bugtracker.baseurl, package_name))
        summary, description = external_bugtracker.getBugSummaryAndDescription(
            remote_bug)
        bug = bug_target.createBug(
            CreateBugParams(
                reporter, summary, description, subscribe_reporter=False))

        [added_task] = bug.bugtasks
        bug_watch = getUtility(IBugWatchSet).createBugWatch(
            bug=bug,
            owner=getUtility(ILaunchpadCelebrities).bug_watch_updater,
            bugtracker=bugtracker, remotebug=remote_bug)

        added_task.bugwatch = bug_watch
        # Need to flush databse updates, so that the bug watch knows it
        # is linked from a bug task.
        flush_database_updates()

        return bug
