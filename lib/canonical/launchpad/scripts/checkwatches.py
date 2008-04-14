# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Helper functions for the checkwatches.py cronscript."""

__metaclass__ = type


from datetime import datetime, timedelta
from logging import getLogger
import socket
import sys

import pytz

from zope.component import getUtility

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.components import externalbugtracker
from canonical.launchpad.components.externalbugtracker import (
    BugNotFound, BugTrackerConnectError, BugWatchUpdateError,
    BugWatchUpdateWarning, InvalidBugId, UnparseableBugData,
    UnparseableBugTrackerVersion, UnsupportedBugTrackerVersion,
    UnknownBugTrackerTypeError, UnknownRemoteStatusError)
from canonical.launchpad.interfaces import (
    BugTaskStatus, BugWatchErrorType, CreateBugParams, IBugTrackerSet,
    IBugWatchSet, IDistribution, ILaunchpadCelebrities, IPersonSet,
    ISupportsCommentImport, PersonCreationRationale,
    UNKNOWN_REMOTE_STATUS)
from canonical.launchpad.webapp.errorlog import (
    ErrorReportingUtility, ScriptRequest)
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


class TooMuchTimeSkew(BugWatchUpdateError):
    """Time difference between ourselves and the remote server is too much."""


#
# OOPS reporting.
#


class CheckWatchesErrorUtility(ErrorReportingUtility):
    """An error utility that for the checkwatches process."""

    _default_config_section = 'checkwatches'


def report_oops(message=None, properties=None, info=None):
    """Record an oops for the current exception.

    This must only be called while handling an exception.

    :param message: custom explanatory error message. Do not use
        str(exception) to fill in this parameter, it should only be
        set when a human readable error has been explicitly generated.

    :param properties: Properties to record in the OOPS report.
    :type properties: An iterable of (name, value) tuples.

    :param info: Exception info.
    :type info: The return value of `sys.exc_info()`.
    """
    # Get the current exception info first of all.
    if info is None:
        info = sys.exc_info()

    # Collect properties to report.
    if properties is None:
        properties = []
    else:
        properties = list(properties)

    if message is not None:
        properties.append(('error-explanation', message))

    # Create the dummy request object.
    request = ScriptRequest(properties)
    error_utility = CheckWatchesErrorUtility()
    error_utility.raising(info, request)

    return request


def report_warning(message, properties=None, info=None):
    """Create and report a warning as an OOPS.

    If no exception info is passed in this will create a generic
    `BugWatchUpdateWarning` to record. The reason is that the stack
    trace may be useful for later diagnosis.

    :param message: See `report_oops`.
    :param properties: See `report_oops`.
    :param info: See `report_oops`.
    """
    if info is None:
        # Raise and catch the exception so that sys.exc_info will
        # return our warning and stack trace.
        try:
            raise BugWatchUpdateWarning
        except BugWatchUpdateWarning:
            return report_oops(message, properties)
    else:
        return report_oops(message, properties, info)


class BugWatchUpdater(object):
    """Takes responsibility for updating remote bug watches."""

    ACCEPTABLE_TIME_SKEW = timedelta(minutes=10)

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
        self.txn.begin()
        ubuntu_bugzilla = getUtility(ILaunchpadCelebrities).ubuntu_bugzilla
        # Save the name, so we can use it in other transactions.
        ubuntu_bugzilla_name = ubuntu_bugzilla.name

        # Set up an interaction as the Bug Watch Updater since the
        # notification code expects a logged in user.
        self._login()

        if bug_tracker_names is None:
            bug_tracker_names = [
                bugtracker.name for bugtracker in getUtility(IBugTrackerSet)]
        self.txn.commit()
        for bug_tracker_name in bug_tracker_names:
            self.txn.begin()
            bug_tracker = getUtility(IBugTrackerSet).getByName(
                bug_tracker_name)
            # Save the url for later, since we might need it to report an
            # error after a transaction has been aborted.
            bug_tracker_url = bug_tracker.baseurl
            try:
                if bug_tracker_name == ubuntu_bugzilla_name:
                    # XXX: 2007-09-11 Graham Binns
                    #      We automatically ignore the Ubuntu Bugzilla
                    #      here as all its bugs have been imported into
                    #      Launchpad. Ideally we would have some means
                    #      to identify all bug trackers like this so
                    #      that hard-coding like this can be genericised
                    #      (Bug 138949).
                    self.log.debug(
                        "Skipping updating Ubuntu Bugzilla watches.")
                else:
                    self.updateBugTracker(bug_tracker)

                self.txn.commit()
            except (KeyboardInterrupt, SystemExit):
                # We should never catch KeyboardInterrupt or SystemExit.
                raise
            except Exception, error:
                # If something unexpected goes wrong, we log it and
                # continue: a failure shouldn't break the updating of
                # the other bug trackers.
                info = sys.exc_info()
                properties = [
                    ('bugtracker', bug_tracker_name),
                    ('baseurl', bug_tracker_url)]
                if isinstance(error, BugWatchUpdateError):
                    self.error(
                        str(error), properties=properties, info=info)
                elif isinstance(error, socket.timeout):
                    self.error(
                        "Connection timed out when updating %s" % 
                        bug_tracker_url,
                        properties=properties, info=info)
                else:
                    self.error(
                        "An exception was raised when updating %s" %
                        bug_tracker_url,
                        properties=properties, info=info)
                self.txn.abort()
        self._logout()

    def _getBugWatch(self, bug_watch_id):
        """Return the bug watch with id `bug_watch_id`."""
        return getUtility(IBugWatchSet).get(bug_watch_id)

    def _getBugWatchesByRemoteBug(self, bug_watch_ids):
        """Returns a dictionary of bug watches mapped to remote bugs.

        For each bug watch id fetches the corresponding bug watch and
        appends it to a list of bug watches pointing to one remote
        bug - the key of the returned mapping.
        """
        bug_watches_by_remote_bug = {}
        for bug_watch_id in bug_watch_ids:
            bug_watch = self._getBugWatch(bug_watch_id)
            remote_bug = bug_watch.remotebug
            # There can be multiple bug watches pointing to the same
            # remote bug; because of that, we need to store lists of bug
            # watches related to the remote bug, and later update the
            # status of each one of them.
            if remote_bug not in bug_watches_by_remote_bug:
                bug_watches_by_remote_bug[remote_bug] = []
            bug_watches_by_remote_bug[remote_bug].append(bug_watch)
        return bug_watches_by_remote_bug

    def _getExternalBugTracker(self, bug_tracker):
        """Return an `ExternalBugTracker` instance for `bug_tracker`."""
        return externalbugtracker.get_external_bugtracker(bug_tracker)

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
                get_bugwatcherrortype_for_error(error))
            for bug_watch in bug_watches_to_update:
                bug_watch.last_error_type = error_type
                bug_watch.lastchecked = UTC_NOW

            message = (
                "ExternalBugtracker for BugTrackerType '%s' is not known." % (
                    error.bugtrackertypename))
            self.warning(message)
        else:
            if bug_watches_to_update.count() > 0:
                self.updateBugWatches(remotesystem, bug_watches_to_update)
            else:
                self.log.debug(
                    "No watches to update on %s" % bug_tracker.baseurl)

    def _convertRemoteStatus(self, remotesystem, remote_status):
        """Convert a remote bug status to a Launchpad status and return it.

        :param remotesystem: The `IExternalBugTracker` instance
            representing the remote system.
        :param remote_status: The remote status to be converted into a
            Launchpad status.

        If the remote status cannot be mapped to a Launchpad status,
        BugTaskStatus.UNKNOWN will be returned and a warning will be
        logged.
        """
        # We don't bother trying to convert UNKNOWN_REMOTE_STATUS.
        if remote_status == UNKNOWN_REMOTE_STATUS:
            return BugTaskStatus.UNKNOWN

        try:
            launchpad_status = remotesystem.convertRemoteStatus(
                remote_status)
        except UnknownRemoteStatusError:
            # We log the warning, since we need to know about statuses
            # that we don't handle correctly.
            self.warning("Unknown remote status '%s'." % remote_status,
                self._getOOPSProperties(remotesystem), sys.exc_info())

            launchpad_status = BugTaskStatus.UNKNOWN

        return launchpad_status

    def _getOldestLastChecked(self, bug_watches):
        """Return the oldest lastchecked attribute of the bug watches."""
        if len(bug_watches) == 0:
            return None
        bug_watch_lastchecked_times = sorted(
            bug_watch.lastchecked
            for bug_watch in bug_watches)
        return bug_watch_lastchecked_times[0]

    def updateBugWatches(self, remotesystem, bug_watches_to_update, now=None):
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
            set(bug_watch.remotebug for bug_watch in bug_watches))
        if remotesystem.batch_size is not None:
            remote_ids = remote_ids[:remotesystem.batch_size]

            for bug_watch in list(bug_watches):
                if bug_watch.remotebug not in remote_ids:
                    bug_watches.remove(bug_watch)

        self.log.info("Updating %i watches on %s" %
            (len(bug_watches), bug_tracker_url))

        old_bug_watches = [
            bug_watch for bug_watch in bug_watches
            if bug_watch.lastchecked is not None]
        oldest_lastchecked = self._getOldestLastChecked(old_bug_watches)
        if oldest_lastchecked is not None:
            # Adjust for possible time skew, and some more, just to be safe.
            oldest_lastchecked -= (
                self.ACCEPTABLE_TIME_SKEW + timedelta(minutes=1))

        remote_old_ids = sorted(
            set(bug_watch.remotebug for bug_watch in old_bug_watches))
        remote_new_ids = sorted(
            set(bug_watch.remotebug for bug_watch in bug_watches
                if bug_watch not in old_bug_watches))

        bug_watch_ids = [bug_watch.id for bug_watch in bug_watches]

        self.txn.commit()
        server_time = None
        if now is None:
            now = datetime.now(pytz.timezone('UTC'))
        try:
            server_time = remotesystem.getCurrentDBTime()
            if (server_time is not None and
                abs(server_time - now) > self.ACCEPTABLE_TIME_SKEW):
                raise TooMuchTimeSkew(abs(server_time - now))

            if len(remote_old_ids) > 0 and server_time is not None:
                old_ids_to_check = remotesystem.getModifiedRemoteBugs(
                    remote_old_ids, oldest_lastchecked)
            else:
                old_ids_to_check = list(remote_old_ids)

            remote_ids_to_check = sorted(
                set(remote_new_ids + old_ids_to_check))
            remotesystem.initializeRemoteBugDB(remote_ids_to_check)
        except Exception, error:
            # We record the error against all the bugwatches that should
            # have been updated before re-raising it. We also update the
            # bug watches' lastchecked dates so that checkwatches
            # doesn't keep trying to update them every time it runs.
            self.txn.begin()
            errortype = get_bugwatcherrortype_for_error(error)
            for bug_watch_id in bug_watch_ids:
                bugwatch = getUtility(IBugWatchSet).get(bug_watch_id)
                bugwatch.lastchecked = UTC_NOW
                bugwatch.last_error_type = errortype
            self.txn.commit()
            raise

        self.txn.begin()
        bug_watches_by_remote_bug = self._getBugWatchesByRemoteBug(
            bug_watch_ids)
        non_modified_bugs = set(remote_ids).difference(remote_ids_to_check)
        can_import_comments = (
            ISupportsCommentImport.providedBy(remotesystem) and
            remotesystem.import_comments)
        if can_import_comments and server_time is None:
            can_import_comments = False
            self.warning(
                "Comment importing supported, but server time can't be"
                " trusted. No comments will be imported.")
        for bug_id in remote_ids:
            bug_watches = bug_watches_by_remote_bug[bug_id]
            for bug_watch in bug_watches:
                bug_watch.lastchecked = UTC_NOW
            if bug_id in non_modified_bugs:
                # No need to try to update it, if it wasn't modified.
                continue

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
                    new_malone_status = self._convertRemoteStatus(
                        remotesystem, new_remote_status)

                    new_remote_importance = remotesystem.getRemoteImportance(
                        bug_id)
                    new_malone_importance = (
                        remotesystem.convertRemoteImportance(
                            new_remote_importance))
                except InvalidBugId:
                    error = BugWatchErrorType.INVALID_BUG_ID
                    self.warning(
                        "Invalid bug %r on %s (local bugs: %s)." %
                             (bug_id, remotesystem.baseurl, local_ids),
                        properties=[
                            ('bug_id', bug_id),
                            ('local_ids', local_ids)] +
                            self._getOOPSProperties(remotesystem),
                        info=sys.exc_info())
                except BugNotFound:
                    error = BugWatchErrorType.BUG_NOT_FOUND
                    self.warning(
                        "Didn't find bug %r on %s (local bugs: %s)." %
                             (bug_id, remotesystem.baseurl, local_ids),
                        properties=[
                            ('bug_id', bug_id),
                            ('local_ids', local_ids)] +
                            self._getOOPSProperties(remotesystem),
                        info=sys.exc_info())

                for bug_watch in bug_watches:
                    bug_watch.last_error_type = error
                    if new_malone_status is not None:
                        bug_watch.updateStatus(new_remote_status,
                            new_malone_status)
                    if new_malone_importance is not None:
                        bug_watch.updateImportance(new_remote_importance,
                            new_malone_importance)
                    if can_import_comments:
                        self.importBugComments(remotesystem, bug_watch)

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
                bug_watches_by_remote_bug = self._getBugWatchesByRemoteBug(
                    bug_watch_ids)

                # We record errors against the bug watches and update
                # their lastchecked dates so that we don't try to
                # re-check them every time checkwatches runs.
                errortype = get_bugwatcherrortype_for_error(error)
                for bugwatch in bug_watches:
                    bugwatch.lastchecked = UTC_NOW
                    bugwatch.last_error_type = errortype
                # We need to commit the transaction, in case the next
                # bug fails to update as well.
                self.txn.commit()
                self.txn.begin()

                self.error(
                    "Failure updating bug %r on %s (local bugs: %s)." %
                            (bug_id, bug_tracker_url, local_ids),
                    properties=[
                        ('bug_id', bug_id),
                        ('local_ids', local_ids)] +
                        self._getOOPSProperties(remotesystem))

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
            self.warning(
                'Unknown %s package (#%s at %s): %s' % (
                    bug_target.name, remote_bug,
                    external_bugtracker.baseurl, package_name))
        summary, description = (
            external_bugtracker.getBugSummaryAndDescription(remote_bug))
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

    def importBugComments(self, external_bugtracker, bug_watch):
        """Import all the comments from a remote bug.

        :param external_bugtracker: An external bugtracker which
            implements `ISupportsCommentImport`.
        :param bug_watch: The bug watch for which the comments should be
            imported.
        """
        imported_comments = 0
        for comment_id in external_bugtracker.getCommentIds(bug_watch):
            displayname, email = external_bugtracker.getPosterForComment(
                bug_watch, comment_id)

            poster = getUtility(IPersonSet).ensurePerson(
                email, displayname, PersonCreationRationale.BUGIMPORT,
                comment='when importing comments for %s.' % bug_watch.title)

            comment_message = external_bugtracker.getMessageForComment(
                bug_watch, comment_id, poster)
            if not bug_watch.hasComment(comment_id):
                bug_watch.addComment(comment_id, comment_message)
                imported_comments += 1

        if imported_comments > 0:
            self.log.info("Imported %(count)i comments for remote bug "
                "%(remotebug)s on %(bugtracker_url)s into Launchpad bug "
                "%(bug_id)s." %
                {'count': imported_comments,
                 'remotebug': bug_watch.remotebug,
                 'bugtracker_url': external_bugtracker.baseurl,
                 'bug_id': bug_watch.bug.id})

    def _getOOPSProperties(self, remotesystem):
        """Return an iterable of 2-tuples (name, value) of OOPS properties.

        :remotesystem: The `ExternalBugTracker` instance from which the
            OOPS properties should be extracted.
        """
        return [('batch_size', remotesystem.batch_size),
                ('batch_query_threshold', remotesystem.batch_query_threshold),
                ('import_comments', remotesystem.import_comments),
                ('externalbugtracker', remotesystem.__class__.__name__),
                ('baseurl', remotesystem.baseurl)]

    def warning(self, message, properties=None, info=None):
        """Record a warning related to this bug tracker."""
        report_warning(message, properties, info)
        # Also put it in the log.
        self.log.warning(message)

    def error(self, message, properties=None, info=None):
        """Record an error related to this external bug tracker."""
        oops_info = report_oops(message, properties, info)

        # Also put it in the log.
        self.log.error("%s (%s)" % (message, oops_info.oopsid))
