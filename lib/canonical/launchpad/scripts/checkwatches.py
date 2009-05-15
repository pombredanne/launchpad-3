# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Helper functions for the checkwatches.py cronscript."""

__metaclass__ = type


from datetime import datetime, timedelta
import socket
import sys

import pytz

from zope.component import getUtility
from zope.event import notify

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.components import externalbugtracker
from canonical.launchpad.components.externalbugtracker import (
    BugNotFound, BugTrackerConnectError, BugWatchUpdateError,
    BugWatchUpdateWarning, InvalidBugId, PrivateRemoteBug,
    UnknownBugTrackerTypeError, UnknownRemoteStatusError, UnparseableBugData,
    UnparseableBugTrackerVersion, UnsupportedBugTrackerVersion)
from canonical.launchpad.components.externalbugtracker.bugzilla import (
    BugzillaLPPlugin)
from lazr.lifecycle.event import ObjectCreatedEvent
from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.interfaces import (
    BugTaskStatus, BugWatchErrorType, CreateBugParams,
    IBugTrackerSet, IBugWatchSet, IDistribution, ILaunchpadCelebrities,
    IPersonSet, ISupportsCommentImport, ISupportsCommentPushing,
    PersonCreationRationale, UNKNOWN_REMOTE_STATUS)
from canonical.launchpad.interfaces.bug import IBugSet
from canonical.launchpad.interfaces.externalbugtracker import (
    ISupportsBackLinking)
from canonical.launchpad.interfaces.launchpad import NotFoundError
from canonical.launchpad.interfaces.message import IMessageSet
from canonical.launchpad.scripts.logger import log as default_log
from canonical.launchpad.webapp.errorlog import (
    ErrorReportingUtility, ScriptRequest)
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
from canonical.launchpad.webapp.interaction import (
    setupInteraction, endInteraction)
from canonical.launchpad.webapp.publisher import canonical_url


SYNCABLE_GNOME_PRODUCTS = []


class TooMuchTimeSkew(BugWatchUpdateError):
    """Time difference between ourselves and the remote server is too much."""


_exception_to_bugwatcherrortype = [
   (BugTrackerConnectError, BugWatchErrorType.CONNECTION_ERROR),
   (PrivateRemoteBug, BugWatchErrorType.PRIVATE_REMOTE_BUG),
   (UnparseableBugData, BugWatchErrorType.UNPARSABLE_BUG),
   (UnparseableBugTrackerVersion, BugWatchErrorType.UNPARSABLE_BUG_TRACKER),
   (UnsupportedBugTrackerVersion, BugWatchErrorType.UNSUPPORTED_BUG_TRACKER),
   (UnknownBugTrackerTypeError, BugWatchErrorType.UNSUPPORTED_BUG_TRACKER),
   (InvalidBugId, BugWatchErrorType.INVALID_BUG_ID),
   (BugNotFound, BugWatchErrorType.BUG_NOT_FOUND),
   (PrivateRemoteBug, BugWatchErrorType.PRIVATE_REMOTE_BUG),
   (socket.timeout, BugWatchErrorType.TIMEOUT)]

def get_bugwatcherrortype_for_error(error):
    """Return the correct `BugWatchErrorType` for a given error."""
    for exc_type, bugwatcherrortype in _exception_to_bugwatcherrortype:
        if isinstance(error, exc_type):
            return bugwatcherrortype
    else:
        return BugWatchErrorType.UNKNOWN


#
# OOPS reporting.
#


class CheckWatchesErrorUtility(ErrorReportingUtility):
    """An error utility that for the checkwatches process."""

    _default_config_section = 'checkwatches'


def report_oops(message=None, properties=None, info=None):
    """Record an oops for the current exception.

    This must only be called while handling an exception.

    Searches for 'URL', 'url', or 'baseurl' properties, in order of
    preference, to use as the linked URL of the OOPS report.

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

    # Find a candidate for the request URL.
    def find_url():
        for name in 'URL', 'url', 'baseurl':
            for key, value in properties:
                if key == name:
                    return value
        return None
    url = find_url()

    # Create the dummy request object.
    request = ScriptRequest(properties, url)
    error_utility = CheckWatchesErrorUtility()
    error_utility.raising(info, request)

    return request


def report_warning(message, properties=None, info=None):
    """Create and report a warning as an OOPS.

    If no exception info is passed in this will create a generic
    `BugWatchUpdateWarning` to record.

    :param message: See `report_oops`.
    :param properties: See `report_oops`.
    :param info: See `report_oops`.
    """
    if info is None:
        # Raise and catch the exception so that sys.exc_info will
        # return our warning.
        try:
            raise BugWatchUpdateWarning(message)
        except BugWatchUpdateWarning:
            return report_oops(message, properties)
    else:
        return report_oops(message, properties, info)


class BugWatchUpdater(object):
    """Takes responsibility for updating remote bug watches."""

    ACCEPTABLE_TIME_SKEW = timedelta(minutes=10)

    def __init__(self, txn, log=default_log, syncable_gnome_products=None):
        self.txn = txn
        self.log = log

        # Override SYNCABLE_GNOME_PRODUCTS if necessary.
        if syncable_gnome_products is not None:
            self._syncable_gnome_products = syncable_gnome_products
        else:
            self._syncable_gnome_products = list(SYNCABLE_GNOME_PRODUCTS)

    def _login(self):
        """Set up an interaction as the Bug Watch Updater"""
        auth_utility = getUtility(IPlacelessAuthUtility)
        setupInteraction(
            auth_utility.getPrincipalByLogin(
                'bugwatch@bugs.launchpad.net', want_password=False),
            login='bugwatch@bugs.launchpad.net')

    def _logout(self):
        """Tear down the Bug Watch Updater Interaction."""
        endInteraction()

    def updateBugTrackers(self, bug_tracker_names=None, batch_size=None):
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

        self.log.debug("Using a global batch size of %s" % batch_size)

        if bug_tracker_names is None:
            bug_tracker_names = [
                bugtracker.name for bugtracker in getUtility(IBugTrackerSet)]
        self.txn.commit()
        for bug_tracker_name in bug_tracker_names:
            self.txn.begin()
            bug_tracker = getUtility(IBugTrackerSet).getByName(
                bug_tracker_name)

            if not bug_tracker.active:
                self.log.debug(
                    "Updates are disabled for bug tracker at %s" %
                    bug_tracker.baseurl)
                self.txn.abort()
                continue

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
                    self.updateBugTracker(bug_tracker, batch_size)

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

    def _getExternalBugTrackersAndWatches(self, bug_tracker, bug_watches):
        """Return an `ExternalBugTracker` instance for `bug_tracker`."""
        remotesystem = externalbugtracker.get_external_bugtracker(
            bug_tracker)
        remotesystem_to_use = remotesystem.getExternalBugTrackerToUse()

        # We special-case the Gnome Bugzilla.
        gnome_bugzilla = getUtility(ILaunchpadCelebrities).gnome_bugzilla
        if (bug_tracker == gnome_bugzilla and
            isinstance(remotesystem_to_use, BugzillaLPPlugin)):

            lp_plugin_watches = []
            normal_watches = []

            bug_ids = [bug_watch.remotebug for bug_watch in bug_watches]
            remote_products = remotesystem_to_use.getProductsForRemoteBugs(
                bug_ids)

            # For bug watches on remote bugs that are against products
            # in the _syncable_gnome_products list - i.e. ones with which
            # we want to sync comments - we return a BugzillaLPPlugin
            # instance. Otherwise we return a normal Bugzilla instance.
            for bug_watch in bug_watches:
                if (remote_products[bug_watch.remotebug] in
                    self._syncable_gnome_products):
                    lp_plugin_watches.append(bug_watch)
                else:
                    normal_watches.append(bug_watch)

            trackers_and_watches = [
                (remotesystem_to_use, lp_plugin_watches),
                (remotesystem, normal_watches),
                ]
        else:
            trackers_and_watches = [(remotesystem_to_use, bug_watches)]

        return trackers_and_watches

    def updateBugTracker(self, bug_tracker, batch_size=None):
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

        if bug_watches_to_update.count() > 0:
            try:
                trackers_and_watches = self._getExternalBugTrackersAndWatches(
                    bug_tracker, bug_watches_to_update)
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
                    "ExternalBugtracker for BugTrackerType '%s' is not "
                    "known." % (error.bugtrackertypename))
                self.warning(message)
            else:
                for remotesystem, bug_watch_batch in trackers_and_watches:
                    self.updateBugWatches(
                        remotesystem, bug_watch_batch, batch_size=batch_size)
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

    def _getRemoteIdsToCheck(self, remotesystem, bug_watches,
                             server_time=None, now=None, batch_size=None):
        """Return the remote bug IDs to check for a set of bug watches.

        The remote bug tracker is queried to find out which of the
        remote bugs in `bug_watches` have changed since they were last
        checked. Those which haven't changed are excluded.

        :param bug_watches: A set of `BugWatch`es to be checked.
        :param remotesystem: The `ExternalBugtracker` on which
            `getModifiedRemoteBugs`() should be called
        :param server_time: The time according to the remote server.
            This may be None when the server doesn't specify a remote time.
        :param now: The current time (used for testing)
        :return: A list of remote bug IDs to be updated.
        """
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

        if now is None:
            now = datetime.now(pytz.timezone('UTC'))

        if (server_time is not None and
            abs(server_time - now) > self.ACCEPTABLE_TIME_SKEW):
            raise TooMuchTimeSkew(abs(server_time - now))

        # We only make the call to getModifiedRemoteBugs() if there
        # are actually some bugs that we're interested in so as to
        # avoid unnecessary network traffic.
        elif server_time is not None and len(remote_old_ids) > 0:
            old_ids_to_check = remotesystem.getModifiedRemoteBugs(
                remote_old_ids, oldest_lastchecked)
        else:
            old_ids_to_check = list(remote_old_ids)

        # We bypass the has-it-been-checked tests for bug watches with
        # unpushed comments.
        remote_ids_with_comments = sorted(
            set(bug_watch.remotebug for bug_watch in bug_watches
                if bug_watch.unpushed_comments.any() is not None))

        remote_ids_to_check = sorted(
            set(remote_ids_with_comments)) + sorted(remote_new_ids)

        # We remove any IDs that are already in remote_ids_to_check from
        # old_ids_to_check, since we're already going to be checking
        # them anyway.
        old_ids_to_check = sorted(
            set(old_ids_to_check).difference(set(remote_ids_to_check)))

        # We limit the number of watches we're updating by the
        # ExternalBugTracker's batch_size. In an ideal world we'd just
        # slice the bug_watches list but for the sake of testing we need
        # to ensure that the list of bug watches is ordered by remote
        # bug id before we do so.
        if batch_size is None:
            # If a batch_size hasn't been passed, use the one specified
            # by the ExternalBugTracker.
            batch_size = remotesystem.batch_size

        if batch_size == 0:
            # A batch_size of 0 means that there's no batch size limit
            # for this bug tracker.
            batch_size = None

        if batch_size is not None:
            # We'll recreate our remote_ids_to_check list so that it's
            # prioritised. We always include remote ids with comments.
            actual_remote_ids_to_check = sorted(
                remote_ids_with_comments[:batch_size])

            # If there is still room in the batch, add as many 'old' bug
            # watches as possible. We do this in kind of an odd way
            # because we need the ids to go into the list in order of
            # priority:
            #  1. IDs with comments.
            #  2. IDs that haven't been checked.
            #  3. Everything else.
            for id_list in (sorted(remote_new_ids), sorted(old_ids_to_check)):
                # Include first as many IDs from remote_new_ids as
                # possible and then, if there's room as many from
                # old_ids_to_check as possible.
                ids_to_check_count = len(actual_remote_ids_to_check)
                slots_left = batch_size - ids_to_check_count
                if slots_left < 1:
                    continue

                actual_remote_ids_to_check = (
                    actual_remote_ids_to_check + id_list[:slots_left])

            # Now that we've worked out which IDs we want to check we
            # can sort the list.
            remote_ids_to_check = sorted(set(actual_remote_ids_to_check))
        else:
            # If there's no batch size specified, update everything.
            remote_ids_to_check = sorted(
                set(old_ids_to_check).union(remote_ids_to_check))

        # Make sure that unmodified_remote_ids only includes IDs that
        # could have been checked but which weren't modified on the
        # remote server and which haven't been listed for checking
        # otherwise (i.e. because they have comments to be pushed).
        unmodified_old_ids = set(
            remote_old_ids).difference(set(old_ids_to_check))
        unmodified_remote_ids = [
            remote_id for remote_id in unmodified_old_ids
            if remote_id not in remote_ids_to_check]

        all_remote_ids = remote_ids_to_check + unmodified_remote_ids
        return {
            'remote_ids_to_check': remote_ids_to_check,
            'all_remote_ids': all_remote_ids,
            'unmodified_remote_ids': unmodified_remote_ids,
            }

    # XXX gmb 2008-11-07 [bug=295319]
    #     This method is 186 lines long. It needs to be shorter.
    def updateBugWatches(self, remotesystem, bug_watches_to_update, now=None,
                         batch_size=None):
        """Update the given bug watches."""
        # Save the url for later, since we might need it to report an
        # error after a transaction has been aborted.
        bug_tracker_url = remotesystem.baseurl

        # Some tests pass a list of bug watches whilst checkwatches.py
        # will pass a SelectResults instance. We convert bug_watches to a
        # list here to ensure that were're doing sane things with it
        # later on.
        bug_watches = list(bug_watches_to_update)
        bug_watch_ids = [bug_watch.id for bug_watch in bug_watches]

        # Fetch the time on the server. We'll use this in
        # _getRemoteIdsToCheck() and when determining whether we can
        # sync comments or not.
        self.txn.commit()
        server_time = remotesystem.getCurrentDBTime()
        try:
            remote_ids = self._getRemoteIdsToCheck(
                remotesystem, bug_watches, server_time, now, batch_size)
        except TooMuchTimeSkew, error:
            # If there's too much time skew we can't continue with this
            # run.
            self.txn.begin()
            errortype = get_bugwatcherrortype_for_error(error)
            for bug_watch_id in bug_watch_ids:
                bugwatch = getUtility(IBugWatchSet).get(bug_watch_id)
                bugwatch.lastchecked = UTC_NOW
                bugwatch.last_error_type = errortype
            self.txn.commit()
            raise

        remote_ids_to_check = remote_ids['remote_ids_to_check']
        all_remote_ids = remote_ids['all_remote_ids']
        unmodified_remote_ids = remote_ids['unmodified_remote_ids']

        # Remove from the list of bug watches any watch whose remote ID
        # doesn't appear in the list of IDs to check.
        for bug_watch in list(bug_watches):
            if bug_watch.remotebug not in remote_ids_to_check:
                bug_watches.remove(bug_watch)


        self.log.info("Updating %i watches for %i bugs on %s" %
            (len(bug_watches), len(remote_ids_to_check),
            bug_tracker_url))

        try:
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

        # Whether we can import and / or push comments is determined on
        # a per-bugtracker-type level.
        can_import_comments = (
            ISupportsCommentImport.providedBy(remotesystem) and
            remotesystem.sync_comments)
        can_push_comments = (
            ISupportsCommentPushing.providedBy(remotesystem) and
            remotesystem.sync_comments)

        if can_import_comments and server_time is None:
            can_import_comments = False
            self.warning(
                "Comment importing supported, but server time can't be"
                " trusted. No comments will be imported.")

        error_type_messages = {
            BugWatchErrorType.INVALID_BUG_ID:
                ("Invalid bug %(bug_id)r on %(base_url)s "
                 "(local bugs: %(local_ids)s)."),
            BugWatchErrorType.BUG_NOT_FOUND:
                ("Didn't find bug %(bug_id)r on %(base_url)s "
                 "(local bugs: %(local_ids)s)."),
            BugWatchErrorType.PRIVATE_REMOTE_BUG:
                ("Remote bug %(bug_id)r on %(base_url)s is private "
                 "(local bugs: %(local_ids)s)."),
            }
        error_type_message_default = (
            "remote bug: %(bug_id)r; "
            "base url: %(base_url)s; "
            "local bugs: %(local_ids)s"
            )

        for bug_id in all_remote_ids:
            bug_watches = bug_watches_by_remote_bug[bug_id]
            for bug_watch in bug_watches:
                bug_watch.lastchecked = UTC_NOW
            if bug_id in unmodified_remote_ids:
                continue

            # Save the remote bug URL in case we need to log an error.
            remote_bug_url = bug_watches[0].url

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
                except (InvalidBugId, BugNotFound, PrivateRemoteBug), ex:
                    error = get_bugwatcherrortype_for_error(ex)
                    message = error_type_messages.get(
                        error, error_type_message_default)
                    self.warning(
                        message % {
                            'bug_id': bug_id,
                            'base_url': remotesystem.baseurl,
                            'local_ids': local_ids,
                            },
                        properties=[
                            ('URL', remote_bug_url),
                            ('bug_id', bug_id),
                            ('local_ids', local_ids),
                            ] + self._getOOPSProperties(remotesystem),
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
                    if can_push_comments:
                        self.pushBugComments(remotesystem, bug_watch)
                    if ISupportsBackLinking.providedBy(remotesystem):
                        self.linkLaunchpadBug(remotesystem, bug_watch)

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
                        ('URL', remote_bug_url),
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
                reporter, summary, description, subscribe_owner=False,
                filed_by=getUtility(ILaunchpadCelebrities).bug_watch_updater))
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
        # Construct a list of the comment IDs we want to import; i.e.
        # those which we haven't already imported.
        all_comment_ids = external_bugtracker.getCommentIds(bug_watch)
        comment_ids_to_import = [
            comment_id for comment_id in all_comment_ids
            if not bug_watch.hasComment(comment_id)]

        external_bugtracker.fetchComments(bug_watch, comment_ids_to_import)

        previous_imported_comments = bug_watch.getImportedBugMessages()
        is_initial_import = previous_imported_comments.count() == 0
        imported_comments = []
        for comment_id in comment_ids_to_import:
            displayname, email = external_bugtracker.getPosterForComment(
                bug_watch, comment_id)

            if displayname is None and email is None:
                # If we don't have a displayname or an email address
                # then we can't create a Launchpad Person as the author
                # of this comment. We raise an OOPS and continue.
                self.warning(
                    "Unable to import remote comment author. No email "
                    "address or display name found.",
                    self._getOOPSProperties(external_bugtracker),
                    sys.exc_info())
                continue

            poster = bug_watch.bugtracker.ensurePersonForSelf(
                displayname, email, PersonCreationRationale.BUGIMPORT,
                "when importing comments for %s." % bug_watch.title)

            comment_message = external_bugtracker.getMessageForComment(
                bug_watch, comment_id, poster)

            bug_message = bug_watch.addComment(comment_id, comment_message)
            imported_comments.append(bug_message)

        if len(imported_comments) > 0:
            bug_watch_updater = (
                getUtility(ILaunchpadCelebrities).bug_watch_updater)
            if is_initial_import:
                notification_text = get_email_template(
                    'bugwatch-initial-comment-import.txt') % dict(
                        num_of_comments=len(imported_comments),
                        bug_watch_url=bug_watch.url)
                comment_text_template = get_email_template(
                    'bugwatch-comment.txt')

                for bug_message in imported_comments:
                    comment = bug_message.message
                    notification_text += comment_text_template % dict(
                        comment_date=comment.datecreated.isoformat(),
                        commenter=comment.owner.displayname,
                        comment_text=comment.text_contents,
                        comment_reply_url=canonical_url(comment))
                notification_message = getUtility(IMessageSet).fromText(
                    subject=bug_watch.bug.followup_subject(),
                    content=notification_text,
                    owner=bug_watch_updater)
                bug_watch.bug.addCommentNotification(notification_message)
            else:
                for bug_message in imported_comments:
                    notify(ObjectCreatedEvent(
                        bug_message,
                        user=bug_watch_updater))
            self.log.info("Imported %(count)i comments for remote bug "
                "%(remotebug)s on %(bugtracker_url)s into Launchpad bug "
                "%(bug_id)s." %
                {'count': len(imported_comments),
                 'remotebug': bug_watch.remotebug,
                 'bugtracker_url': external_bugtracker.baseurl,
                 'bug_id': bug_watch.bug.id})

    def _formatRemoteComment(self, external_bugtracker, bug_watch, message):
        """Format a comment for a remote bugtracker and return it."""
        comment_template = get_email_template(
            external_bugtracker.comment_template)

        return comment_template % {
            'launchpad_bug': bug_watch.bug.id,
            'comment_author': message.owner.displayname,
            'comment_body': message.text_contents,
            }

    def pushBugComments(self, external_bugtracker, bug_watch):
        """Push Launchpad comments to the remote bug.

        :param external_bugtracker: An external bugtracker which
            implements `ISupportsCommentPushing`.
        :param bug_watch: The bug watch to which the comments should be
            pushed.
        """
        pushed_comments = 0

        # Loop over the unpushed comments for the bug watch.
        # We only push those comments that haven't been pushed
        # already. We don't push any comments not associated with
        # the bug watch.
        for unpushed_comment in bug_watch.unpushed_comments:
            message = unpushed_comment.message

            # Format the comment so that it includes information
            # about the Launchpad bug.
            formatted_comment = self._formatRemoteComment(
                external_bugtracker, bug_watch, message)

            remote_comment_id = (
                external_bugtracker.addRemoteComment(
                    bug_watch.remotebug, formatted_comment,
                    message.rfc822msgid))

            assert remote_comment_id is not None, (
                "A remote_comment_id must be specified.")
            unpushed_comment.remote_comment_id = remote_comment_id

            pushed_comments += 1

        if pushed_comments > 0:
            self.log.info("Pushed %(count)i comments to remote bug "
                "%(remotebug)s on %(bugtracker_url)s from Launchpad bug "
                "%(bug_id)s" %
                {'count': pushed_comments,
                 'remotebug': bug_watch.remotebug,
                 'bugtracker_url': external_bugtracker.baseurl,
                 'bug_id': bug_watch.bug.id})

    def linkLaunchpadBug(self, remotesystem, bug_watch):
        """Link a Launchpad bug to a given remote bug."""
        current_launchpad_id = remotesystem.getLaunchpadBugId(
            bug_watch.remotebug)

        if current_launchpad_id is None:
            # If no bug is linked to the remote bug, link this one and
            # then stop.
            remotesystem.setLaunchpadBugId(
                bug_watch.remotebug, bug_watch.bug.id)
            return

        elif current_launchpad_id == bug_watch.bug.id:
            # If the current_launchpad_id is the same as the ID of the bug
            # we're trying to link, we can stop.
            return

        else:
            # If the current_launchpad_id isn't the same as the one
            # we're trying to link, check that the other bug actually
            # links to the remote bug. If it does, we do nothing, since
            # the first valid link wins. Otherwise we link the bug that
            # we've been passed, overwriting the previous value of the
            # Launchpad bug ID for this remote bug.
            try:
                other_launchpad_bug = getUtility(IBugSet).get(
                    current_launchpad_id)

                other_bug_watch = other_launchpad_bug.getBugWatch(
                    bug_watch.bugtracker, bug_watch.remotebug)
            except NotFoundError:
                # If we can't find the bug that's referenced by
                # current_launchpad_id we simply set other_bug_watch to
                # None so that the Launchpad ID of the remote bug can be
                # set correctly.
                other_bug_watch = None

            if other_bug_watch is None:
                remotesystem.setLaunchpadBugId(
                    bug_watch.remotebug, bug_watch.bug.id)

    def _getOOPSProperties(self, remotesystem):
        """Return an iterable of 2-tuples (name, value) of OOPS properties.

        :remotesystem: The `ExternalBugTracker` instance from which the
            OOPS properties should be extracted.
        """
        return [('batch_size', remotesystem.batch_size),
                ('batch_query_threshold', remotesystem.batch_query_threshold),
                ('sync_comments', remotesystem.sync_comments),
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
