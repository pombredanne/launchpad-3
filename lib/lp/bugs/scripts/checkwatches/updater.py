# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Classes and logic for the checkwatches cronscript."""

from __future__ import with_statement

__metaclass__ = type
__all__ = [
    'BaseScheduler',
    'BugWatchUpdater',
    'CheckWatchesCronScript',
    'CheckWatchesErrorUtility',
    'externalbugtracker',
    'report_oops',
    'SerialScheduler',
    'TooMuchTimeSkew',
    'TwistedThreadScheduler',
    ]

import socket
import sys
import threading
import time

from contextlib import contextmanager
from copy import copy
from datetime import datetime, timedelta
from functools import wraps
from itertools import chain, islice

import pytz

from twisted.internet import reactor
from twisted.internet.defer import DeferredList
from twisted.internet.threads import deferToThreadPool
from twisted.python.threadpool import ThreadPool

from zope.component import getUtility
from zope.event import notify

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import flush_database_updates
from lazr.lifecycle.event import ObjectCreatedEvent
from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.interfaces import (
    BugTaskStatus, BugWatchActivityStatus, CreateBugParams,
    IBugTrackerSet, IBugWatchSet, IDistribution, ILaunchpadCelebrities,
    IPersonSet, ISupportsCommentImport, ISupportsCommentPushing,
    PersonCreationRationale, UNKNOWN_REMOTE_STATUS)
from canonical.launchpad.interfaces.launchpad import NotFoundError
from canonical.launchpad.interfaces.message import IMessageSet
from canonical.launchpad.scripts.logger import log as default_log
from canonical.launchpad.webapp.adapter import (
    clear_request_started, get_request_start_time, set_request_started)
from canonical.launchpad.webapp.errorlog import (
    ErrorReportingUtility, ScriptRequest)
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
from canonical.launchpad.webapp.interaction import (
    setupInteraction, endInteraction, queryInteraction)
from canonical.launchpad.webapp.publisher import canonical_url

from lp.bugs import externalbugtracker
from lp.bugs.externalbugtracker import (
    BATCH_SIZE_UNLIMITED, BugNotFound, BugTrackerConnectError,
    BugWatchUpdateError, BugWatchUpdateWarning, InvalidBugId,
    PrivateRemoteBug, UnknownBugTrackerTypeError, UnknownRemoteStatusError,
    UnparseableBugData, UnparseableBugTrackerVersion,
    UnsupportedBugTrackerVersion)
from lp.bugs.externalbugtracker.isolation import check_no_transaction
from lp.bugs.interfaces.bug import IBugSet
from lp.bugs.interfaces.externalbugtracker import ISupportsBackLinking
from lp.services.limitedlist import LimitedList
from lp.services.scripts.base import LaunchpadCronScript


# The login of the user to run as.
LOGIN = 'bugwatch@bugs.launchpad.net'

# A list of product names for which comments should be synchronized.
SYNCABLE_GNOME_PRODUCTS = []

# For OOPS reporting keep up to this number of SQL statements.
MAX_SQL_STATEMENTS_LOGGED = 10000

# When syncing with a remote bug tracker that reports its idea of the
# current time, this defined the maximum acceptable skew between the
# local and remote clock.
ACCEPTABLE_TIME_SKEW = timedelta(minutes=10)

# The minimum batch size to suggest to an IExternalBugTracker.
SUGGESTED_BATCH_SIZE_MIN = 100
# The proportion of all watches to suggest as a batch size.
SUGGESTED_BATCH_SIZE_PROPORTION = 0.02


class TooMuchTimeSkew(BugWatchUpdateError):
    """Time difference between ourselves and the remote server is too much."""


_exception_to_bugwatcherrortype = [
   (BugTrackerConnectError, BugWatchActivityStatus.CONNECTION_ERROR),
   (PrivateRemoteBug, BugWatchActivityStatus.PRIVATE_REMOTE_BUG),
   (UnparseableBugData, BugWatchActivityStatus.UNPARSABLE_BUG),
   (UnparseableBugTrackerVersion,
    BugWatchActivityStatus.UNPARSABLE_BUG_TRACKER),
   (UnsupportedBugTrackerVersion,
    BugWatchActivityStatus.UNSUPPORTED_BUG_TRACKER),
   (UnknownBugTrackerTypeError,
    BugWatchActivityStatus.UNSUPPORTED_BUG_TRACKER),
   (InvalidBugId, BugWatchActivityStatus.INVALID_BUG_ID),
   (BugNotFound, BugWatchActivityStatus.BUG_NOT_FOUND),
   (PrivateRemoteBug, BugWatchActivityStatus.PRIVATE_REMOTE_BUG),
   (socket.timeout, BugWatchActivityStatus.TIMEOUT)]

def get_bugwatcherrortype_for_error(error):
    """Return the correct `BugWatchActivityStatus` for a given error."""
    for exc_type, bugwatcherrortype in _exception_to_bugwatcherrortype:
        if isinstance(error, exc_type):
            return bugwatcherrortype
    else:
        return BugWatchActivityStatus.UNKNOWN


class CheckWatchesErrorUtility(ErrorReportingUtility):
    """An error utility that for the checkwatches process."""

    _default_config_section = 'checkwatches'


def report_oops(message=None, properties=None, info=None,
                transaction_manager=None):
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

    :param transaction_manager: A transaction manager. If specified,
        further commit() calls will be logged.
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


def report_warning(message, properties=None, info=None,
                   transaction_manager=None):
    """Create and report a warning as an OOPS.

    If no exception info is passed in this will create a generic
    `BugWatchUpdateWarning` to record.

    :param message: See `report_oops`.
    :param properties: See `report_oops`.
    :param info: See `report_oops`.
    :param transaction_manager: See `report_oops`.
    """
    if info is None:
        # Raise and catch the exception so that sys.exc_info will
        # return our warning.
        try:
            raise BugWatchUpdateWarning(message)
        except BugWatchUpdateWarning:
            return report_oops(message, properties)
    else:
        return report_oops(message, properties, info, transaction_manager)


class WorkingBase:
    """A base class for writing a long-running process."""

    def __init__(self, login, transaction_manager, logger):
        self._login = login
        self._principal = (
            getUtility(IPlacelessAuthUtility).getPrincipalByLogin(
                self._login, want_password=False))
        self._transaction_manager = transaction_manager
        self.logger = logger

    @property
    @contextmanager
    def interaction(self):
        """Context manager for interaction as the Bug Watch Updater.

        If an interaction is already in progress this is a no-op,
        otherwise it sets up an interaction on entry and ends it on
        exit.
        """
        if queryInteraction() is None:
            setupInteraction(self._principal, login=self._login)
            try:
                yield
            finally:
                endInteraction()
        else:
            yield

    @property
    @contextmanager
    def transaction(self):
        """Context manager to ring-fence database activity.

        Ensures that no transaction is in progress on entry, and
        commits on a successful exit. Exceptions are propagated once
        the transaction has been aborted.

        This intentionally cannot be nested. Keep it simple.
        """
        check_no_transaction()
        try:
            yield self._transaction_manager
        except:
            self._transaction_manager.abort()
            # Let the exception propagate.
            raise
        else:
            self._transaction_manager.commit()

    def _statement_logging_start(self):
        """Start logging SQL statements and other database activity."""
        set_request_started(
            request_statements=LimitedList(MAX_SQL_STATEMENTS_LOGGED),
            txn=self._transaction_manager, enable_timeout=False)

    def _statement_logging_stop(self):
        """Stop logging SQL statements."""
        clear_request_started()

    def _statement_logging_reset(self):
        """Reset the SQL statement log, if enabled."""
        if get_request_start_time() is not None:
            self._statement_logging_stop()
            self._statement_logging_start()

    @property
    @contextmanager
    def statement_logging(self):
        """Context manager to start and stop SQL statement logging.

        It does this by (mis)using the webapp statement logging
        machinery.
        """
        self._statement_logging_start()
        try:
            yield
        finally:
            self._statement_logging_stop()

    def warning(self, message, properties=None, info=None):
        """Record a warning."""
        oops_info = report_warning(
            message, properties, info, self._transaction_manager)
        # Also put it in the log.
        self.logger.warning("%s (%s)" % (message, oops_info.oopsid))
        # Reset statement logging, if enabled.
        self._statement_logging_reset()
        # Return the OOPS ID so that we can use it in
        # BugWatchActivity.
        return oops_info.oopsid

    def error(self, message, properties=None, info=None):
        """Record an error."""
        oops_info = report_oops(
            message, properties, info, self._transaction_manager)
        # Also put it in the log.
        self.logger.error("%s (%s)" % (message, oops_info.oopsid))
        # Reset statement logging, if enabled.
        self._statement_logging_reset()
        # Return the OOPS ID so that we can use it in
        # BugWatchActivity.
        return oops_info.oopsid


def with_interaction(func):
    """Wrap a method to ensure that it runs within an interaction.

    If an interaction is already set up, this simply calls the
    function. If no interaction exists, it will set one up, call the
    function, then end the interaction.

    This is intended to make sure the right thing happens whether or not
    the function is run in a different thread.

    It's intended for use with `WorkingBase`, which provides an
    `interaction` property; this is the hook that's required.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with self.interaction:
            return func(self, *args, **kwargs)
    return wrapper


def commit_before(func):
    """Wrap a method to commit any in-progress transactions.

    This is chiefly intended for use with public-facing methods, so
    that callers do not need to be responsible for committing before
    calling them.

    It's intended for use with `WorkingBase`, which provides a
    `_transaction_manager` property; this is the hook that's required.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        self._transaction_manager.commit()
        return func(self, *args, **kwargs)
    return wrapper


def unique(iterator):
    """Generate only unique items from an iterator."""
    seen = set()
    for item in iterator:
        if item not in seen:
            seen.add(item)
            yield item


def suggest_batch_size(remote_system, num_watches):
    """Suggest a value for batch_size if it's not set.

    Given the number of bug watches for a `remote_system`, this sets a
    suggested batch size on it. If `remote_system` already has a batch
    size set, this does not override it.

    :param remote_system: An `ExternalBugTracker`.
    :param num_watches: The number of watches for `remote_system`.
    """
    if remote_system.batch_size is None:
        remote_system.batch_size = max(
            SUGGESTED_BATCH_SIZE_MIN,
            int(SUGGESTED_BATCH_SIZE_PROPORTION * num_watches))


def get_remote_system_oops_properties(remote_system):
    """Return (name, value) tuples describing a remote system.

    Each item in the list is intended for use as an OOPS property.

    :remote_system: The `ExternalBugTracker` instance from which the
        OOPS properties should be extracted.
    """
    return [
        ('batch_size', remote_system.batch_size),
        ('batch_query_threshold', remote_system.batch_query_threshold),
        ('sync_comments', remote_system.sync_comments),
        ('externalbugtracker', remote_system.__class__.__name__),
        ('baseurl', remote_system.baseurl)
        ]


class BugWatchUpdater(WorkingBase):
    """Takes responsibility for updating remote bug watches."""

    def __init__(self, transaction_manager, logger=default_log,
                 syncable_gnome_products=None):
        """Initialize a BugWatchUpdater.

        :param transaction_manager: A transaction manager on which
            `begin()`, `abort()` and `commit()` can be
            called. Additionally, it should be safe for different
            threads to use its methods to manage their own
            transactions (i.e. with thread-local storage).

        :param log: An instance of `logging.Logger`, or something that
            provides a similar interface.

        """
        super(BugWatchUpdater, self).__init__(
            LOGIN, transaction_manager, logger)

        # Override SYNCABLE_GNOME_PRODUCTS if necessary.
        if syncable_gnome_products is not None:
            self._syncable_gnome_products = syncable_gnome_products
        else:
            self._syncable_gnome_products = list(SYNCABLE_GNOME_PRODUCTS)

    @with_interaction
    def _bugTrackerUpdaters(self, bug_tracker_names=None):
        """Yields functions that can be used to update each bug tracker."""
        with self.transaction:
            ubuntu_bugzilla = (
                getUtility(ILaunchpadCelebrities).ubuntu_bugzilla)
            # Save the name, so we can use it in other transactions.
            ubuntu_bugzilla_name = ubuntu_bugzilla.name
            # Get all bug tracker names if none have been specified.
            if bug_tracker_names is None:
                bug_tracker_names = sorted(getUtility(IBugTrackerSet).names)

        def make_updater(bug_tracker_name, bug_tracker_id):
            """Returns a function that can update the given bug tracker."""
            def updater(batch_size=None):
                thread = threading.currentThread()
                thread_name = thread.getName()
                thread.setName(bug_tracker_name)
                try:
                    with self.statement_logging:
                        return self.updateBugTracker(
                            bug_tracker_id, batch_size)
                finally:
                    thread.setName(thread_name)
            return updater

        for bug_tracker_name in bug_tracker_names:
            if bug_tracker_name == ubuntu_bugzilla_name:
                # XXX: 2007-09-11 Graham Binns
                #      We automatically ignore the Ubuntu Bugzilla
                #      here as all its bugs have been imported into
                #      Launchpad. Ideally we would have some means
                #      to identify all bug trackers like this so
                #      that hard-coding like this can be genericised
                #      (Bug 138949).
                self.logger.debug(
                    "Skipping updating Ubuntu Bugzilla watches.")
            else:
                with self.transaction:
                    bug_tracker = getUtility(
                        IBugTrackerSet).getByName(bug_tracker_name)
                    bug_tracker_id = bug_tracker.id
                    bug_tracker_active = bug_tracker.active
                    bug_tracker_baseurl = bug_tracker.baseurl

                if bug_tracker_active:
                    yield make_updater(bug_tracker_name, bug_tracker_id)
                else:
                    self.logger.debug(
                        "Updates are disabled for bug tracker at %s" %
                        bug_tracker_baseurl)

    @commit_before
    def updateBugTrackers(
        self, bug_tracker_names=None, batch_size=None, scheduler=None):
        """Update all the bug trackers that have watches pending.

        If bug tracker names are specified in bug_tracker_names only
        those bug trackers will be checked.

        A custom scheduler can be passed in. This should inherit from
        `BaseScheduler`. If no scheduler is given, `SerialScheduler`
        will be used, which simply runs the jobs in order.
        """
        if batch_size is None:
            self.logger.debug("No global batch size specified.")
        elif batch_size == BATCH_SIZE_UNLIMITED:
            self.logger.debug("Using an unlimited global batch size.")
        else:
            self.logger.debug("Using a global batch size of %s" % batch_size)

        # Default to using the very simple SerialScheduler.
        if scheduler is None:
            scheduler = SerialScheduler()

        # Schedule all the jobs to run.
        for updater in self._bugTrackerUpdaters(bug_tracker_names):
            scheduler.schedule(updater, batch_size)

        # Run all the jobs.
        scheduler.run()

    @commit_before
    @with_interaction
    def updateBugTracker(self, bug_tracker, batch_size):
        """Updates the given bug trackers's bug watches.

        If there is an error, logs are updated, and the transaction is
        aborted.

        :param bug_tracker: An IBugTracker or the ID of one, so that this
            method can be called from a different interaction.

        :return: A boolean indicating if the operation was successful.
        """
        with self.transaction:
            # Get the bug tracker.
            if isinstance(bug_tracker, (int, long)):
                bug_tracker = getUtility(IBugTrackerSet).get(bug_tracker)
            # Save the name and url for later, since we might need it
            # to report an error after a transaction has been aborted.
            bug_tracker_name = bug_tracker.name
            bug_tracker_url = bug_tracker.baseurl

        try:
            self._updateBugTracker(bug_tracker, batch_size)
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
            return False
        else:
            return True

    @commit_before
    @with_interaction
    def forceUpdateAll(self, bug_tracker_name, batch_size):
        """Update all the watches for `bug_tracker_name`.

        :param bug_tracker_name: The name of the bug tracker to update.
        :param batch_size: The number of bug watches to update in one
            go. If zero, all bug watches will be updated.
        """
        with self.transaction:
            bug_tracker = getUtility(
                IBugTrackerSet).getByName(bug_tracker_name)
            if bug_tracker is None:
                # If the bug tracker is nonsense then just ignore it.
                self.logger.info(
                    "Bug tracker '%s' doesn't exist. Ignoring." %
                    bug_tracker_name)
                return
            elif bug_tracker.watches.count() == 0:
                # If there are no watches to update, ignore the bug tracker.
                self.logger.info(
                    "Bug tracker '%s' doesn't have any watches. Ignoring." %
                    bug_tracker_name)
                return
            # Reset all the bug watches for the bug tracker.
            self.logger.info(
                "Resetting %s bug watches for bug tracker '%s'" %
                (bug_tracker.watches.count(), bug_tracker_name))
            bug_tracker.resetWatches()

        # Loop over the bug watches in batches as specificed by
        # batch_size until there are none left to update.
        with self.transaction:
            self.logger.info(
                "Updating %s watches on bug tracker '%s'" %
                (bug_tracker.watches.count(), bug_tracker_name))
        has_watches_to_update = True
        while has_watches_to_update:
            if not self.updateBugTracker(bug_tracker, batch_size):
                break
            with self.transaction:
                watches_left = (
                    bug_tracker.watches_needing_update.count())
            self.logger.info(
                "%s watches left to check on bug tracker '%s'" %
                (watches_left, bug_tracker_name))
            has_watches_to_update = watches_left > 0

    def _getExternalBugTrackersAndWatches(self, bug_tracker, bug_watches):
        """Return an `ExternalBugTracker` instance for `bug_tracker`."""
        with self.transaction:
            num_watches = bug_tracker.watches.count()
            remotesystem = (
                externalbugtracker.get_external_bugtracker(bug_tracker))
            # We special-case the Gnome Bugzilla.
            is_gnome_bugzilla = bug_tracker == (
                getUtility(ILaunchpadCelebrities).gnome_bugzilla)

        # Probe the remote system for additional capabilities.
        remotesystem_to_use = remotesystem.getExternalBugTrackerToUse()

        # Try to hint at how many bug watches to check each time.
        suggest_batch_size(remotesystem_to_use, num_watches)

        if (is_gnome_bugzilla and remotesystem_to_use.sync_comments):
            # If there are no products to sync comments for, disable
            # comment sync and return.
            if len(self._syncable_gnome_products) == 0:
                remotesystem_to_use.sync_comments = False
                return [
                    (remotesystem_to_use, bug_watches),
                    ]

            syncable_watches = []
            other_watches = []

            with self.transaction:
                remote_bug_ids = [
                    bug_watch.remotebug for bug_watch in bug_watches]

            remote_products = (
                remotesystem_to_use.getProductsForRemoteBugs(
                    remote_bug_ids))

            with self.transaction:
                for bug_watch in bug_watches:
                    if (remote_products.get(bug_watch.remotebug) in
                        self._syncable_gnome_products):
                        syncable_watches.append(bug_watch)
                    else:
                        other_watches.append(bug_watch)

            # For bug watches on remote bugs that are against products
            # in the _syncable_gnome_products list - i.e. ones with which
            # we want to sync comments - we return a BugzillaAPI
            # instance with sync_comments=True, otherwise we return a
            # similar BugzillaAPI instance, but with sync_comments=False.
            remotesystem_for_syncables = remotesystem_to_use
            remotesystem_for_others = copy(remotesystem_to_use)
            remotesystem_for_others.sync_comments = False

            return [
                (remotesystem_for_syncables, syncable_watches),
                (remotesystem_for_others, other_watches),
                ]
        else:
            return [
                (remotesystem_to_use, bug_watches),
                ]

    def _updateBugTracker(self, bug_tracker, batch_size=None):
        """Updates the given bug trackers's bug watches."""
        with self.transaction:
            bug_watches_to_update = (
                bug_tracker.watches_needing_update)
            bug_watches_need_updating = (
                bug_watches_to_update.count() > 0)

        if bug_watches_need_updating:
            # XXX: GavinPanella 2010-01-18 bug=509223 : Ask remote
            # tracker which remote bugs have been modified, and use
            # this to fill up a batch, rather than figuring out
            # batching later in _getRemoteIdsToCheck().
            try:
                trackers_and_watches = self._getExternalBugTrackersAndWatches(
                    bug_tracker, bug_watches_to_update)
            except UnknownBugTrackerTypeError, error:
                # We update all the bug watches to reflect the fact that
                # this error occurred. We also update their last checked
                # date to ensure that they don't get checked for another
                # 24 hours (see above).
                error_type = (
                    get_bugwatcherrortype_for_error(error))
                with self.transaction:
                    for bug_watch in bug_watches_to_update:
                        bug_watch.last_error_type = error_type
                        bug_watch.lastchecked = UTC_NOW
                        bug_watch.next_check = None
                message = (
                    "ExternalBugtracker for BugTrackerType '%s' is not "
                    "known." % (error.bugtrackertypename))
                self.warning(message)
            else:
                for remotesystem, bug_watch_batch in trackers_and_watches:
                    self.updateBugWatches(
                        remotesystem, bug_watch_batch, batch_size=batch_size)
        else:
            with self.transaction:
                self.logger.debug(
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
            self.warning(
                "Unknown remote status '%s'." % remote_status,
                get_remote_system_oops_properties(remotesystem),
                sys.exc_info())

            launchpad_status = BugTaskStatus.UNKNOWN

        return launchpad_status

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
        # Check that the remote server's notion of time agrees with
        # ours. If not, raise a TooMuchTimeSkew error, since if the
        # server's wrong about the time it'll mess up all our times when
        # we import things.
        if now is None:
            now = datetime.now(pytz.timezone('UTC'))

        if (server_time is not None and
            abs(server_time - now) > ACCEPTABLE_TIME_SKEW):
            raise TooMuchTimeSkew(abs(server_time - now))

        # We limit the number of watches we're updating by the
        # ExternalBugTracker's batch_size. In an ideal world we'd just
        # slice the bug_watches list but for the sake of testing we need
        # to ensure that the list of bug watches is ordered by remote
        # bug id before we do so.
        if batch_size is None:
            # If a batch_size hasn't been passed, use the one specified
            # by the ExternalBugTracker.
            batch_size = remotesystem.batch_size

        with self.transaction:
            old_bug_watches = set(
                bug_watch for bug_watch in bug_watches
                if bug_watch.lastchecked is not None)
            if len(old_bug_watches) == 0:
                oldest_lastchecked = None
            else:
                oldest_lastchecked = min(
                    bug_watch.lastchecked for bug_watch in old_bug_watches)
                # Adjust for possible time skew, and some more, just to be
                # safe.
                oldest_lastchecked -= (
                    ACCEPTABLE_TIME_SKEW + timedelta(minutes=1))
            # Collate the remote IDs.
            remote_old_ids = sorted(
                set(bug_watch.remotebug for bug_watch in old_bug_watches))
            remote_new_ids = sorted(
                set(bug_watch.remotebug for bug_watch in bug_watches
                if bug_watch not in old_bug_watches))
            # If the remote system is not configured to sync comments,
            # don't bother checking for any to push.
            if remotesystem.sync_comments:
                remote_ids_with_comments = sorted(
                    bug_watch.remotebug for bug_watch in bug_watches
                    if bug_watch.unpushed_comments.any() is not None)
            else:
                remote_ids_with_comments = []

        # We only make the call to getModifiedRemoteBugs() if there
        # are actually some bugs that we're interested in so as to
        # avoid unnecessary network traffic.
        if server_time is not None and len(remote_old_ids) > 0:
            if batch_size == BATCH_SIZE_UNLIMITED:
                remote_old_ids_to_check = (
                    remotesystem.getModifiedRemoteBugs(
                        remote_old_ids, oldest_lastchecked))
            else:
                # Don't ask the remote system about more than
                # batch_size bugs at once, but keep asking until we
                # run out of bugs to ask about or we have batch_size
                # bugs to check.
                remote_old_ids_to_check = []
                for index in xrange(0, len(remote_old_ids), batch_size):
                    remote_old_ids_to_check.extend(
                        remotesystem.getModifiedRemoteBugs(
                            remote_old_ids[index : index + batch_size],
                            oldest_lastchecked))
                    if len(remote_old_ids_to_check) >= batch_size:
                        break
        else:
            remote_old_ids_to_check = remote_old_ids

        # We'll create our remote_ids_to_check list so that it's
        # prioritized. We include remote IDs in priority order:
        #  1. IDs with comments.
        #  2. IDs that haven't been checked.
        #  3. Everything else.
        remote_ids_to_check = chain(
            remote_ids_with_comments, remote_new_ids, remote_old_ids_to_check)

        if batch_size != BATCH_SIZE_UNLIMITED:
            # Some remote bug IDs may appear in more than one list so
            # we must filter the list before slicing.
            remote_ids_to_check = islice(
                unique(remote_ids_to_check), batch_size)

        # Stuff the IDs in a set.
        remote_ids_to_check = set(remote_ids_to_check)

        # Make sure that unmodified_remote_ids only includes IDs that
        # could have been checked but which weren't modified on the
        # remote server and which haven't been listed for checking
        # otherwise (i.e. because they have comments to be pushed).
        unmodified_remote_ids = set(remote_old_ids)
        unmodified_remote_ids.difference_update(remote_old_ids_to_check)
        unmodified_remote_ids.difference_update(remote_ids_to_check)

        all_remote_ids = remote_ids_to_check.union(unmodified_remote_ids)
        return {
            'remote_ids_to_check': sorted(remote_ids_to_check),
            'all_remote_ids': sorted(all_remote_ids),
            'unmodified_remote_ids': sorted(unmodified_remote_ids),
            }

    def _getBugWatchesForRemoteBug(self, remote_bug_id, bug_watch_ids):
        """Return a list of bug watches for the given remote bug.

        The returned watches will all be members of `bug_watch_ids`.

        This method exists primarily to be overridden during testing.
        """
        return list(
            getUtility(IBugWatchSet).getBugWatchesForRemoteBug(
                remote_bug_id, bug_watch_ids))

    # XXX gmb 2008-11-07 [bug=295319]
    #     This method is 186 lines long. It needs to be shorter.
    @commit_before
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
        with self.transaction:
            bug_watches = list(bug_watches_to_update)
            bug_watch_ids = [bug_watch.id for bug_watch in bug_watches]

        # Fetch the time on the server. We'll use this in
        # _getRemoteIdsToCheck() and when determining whether we can
        # sync comments or not.
        server_time = remotesystem.getCurrentDBTime()
        try:
            remote_ids = self._getRemoteIdsToCheck(
                remotesystem, bug_watches, server_time, now, batch_size)
        except TooMuchTimeSkew, error:
            # If there's too much time skew we can't continue with this
            # run.
            with self.transaction:
                errortype = get_bugwatcherrortype_for_error(error)
                for bug_watch_id in bug_watch_ids:
                    bugwatch = getUtility(IBugWatchSet).get(bug_watch_id)
                    bugwatch.lastchecked = UTC_NOW
                    bugwatch.next_check = None
                    bugwatch.last_error_type = errortype
            raise

        remote_ids_to_check = remote_ids['remote_ids_to_check']
        all_remote_ids = remote_ids['all_remote_ids']
        unmodified_remote_ids = remote_ids['unmodified_remote_ids']

        # Remove from the list of bug watches any watch whose remote ID
        # doesn't appear in the list of IDs to check.
        with self.transaction:
            for bug_watch in list(bug_watches):
                if bug_watch.remotebug not in remote_ids_to_check:
                    bug_watches.remove(bug_watch)

        self.logger.info(
            "Updating %i watches for %i bugs on %s" % (
                len(bug_watches), len(remote_ids_to_check), bug_tracker_url))

        try:
            remotesystem.initializeRemoteBugDB(remote_ids_to_check)
        except Exception, error:
            # We record the error against all the bugwatches that should
            # have been updated before re-raising it. We also update the
            # bug watches' lastchecked dates so that checkwatches
            # doesn't keep trying to update them every time it runs.
            with self.transaction:
                errortype = get_bugwatcherrortype_for_error(error)
                for bug_watch_id in bug_watch_ids:
                    bugwatch = getUtility(IBugWatchSet).get(bug_watch_id)
                    bugwatch.lastchecked = UTC_NOW
                    bugwatch.next_check = None
                    bugwatch.last_error_type = errortype
            raise

        # Whether we can import and / or push comments is determined
        # on a per-bugtracker-type level.
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
            BugWatchActivityStatus.INVALID_BUG_ID:
                ("Invalid bug %(bug_id)r on %(base_url)s "
                 "(local bugs: %(local_ids)s)."),
            BugWatchActivityStatus.BUG_NOT_FOUND:
                ("Didn't find bug %(bug_id)r on %(base_url)s "
                 "(local bugs: %(local_ids)s)."),
            BugWatchActivityStatus.PRIVATE_REMOTE_BUG:
                ("Remote bug %(bug_id)r on %(base_url)s is private "
                 "(local bugs: %(local_ids)s)."),
            }
        error_type_message_default = (
            "remote bug: %(bug_id)r; "
            "base url: %(base_url)s; "
            "local bugs: %(local_ids)s"
            )

        for remote_bug_id in all_remote_ids:
            with self.transaction:
                bug_watches = self._getBugWatchesForRemoteBug(
                    remote_bug_id, bug_watch_ids)
                # If there aren't any bug watches for this remote bug,
                # just log a warning and carry on.
                if len(bug_watches) == 0:
                    self.warning(
                        "Spurious remote bug ID: No watches found for "
                        "remote bug %s on %s" % (
                            remote_bug_id, remotesystem.baseurl))
                    continue
                # Mark them all as checked.
                for bug_watch in bug_watches:
                    bug_watch.lastchecked = UTC_NOW
                    bug_watch.next_check = None
                # Next if this one is definitely unmodified.
                if remote_bug_id in unmodified_remote_ids:
                    continue
                # Save the remote bug URL for error reporting.
                remote_bug_url = bug_watches[0].url
                # Save the list of local bug IDs for error reporting.
                local_ids = ", ".join(
                    str(bug_id) for bug_id in sorted(
                        watch.bug.id for watch in bug_watches))

            try:
                new_remote_status = None
                new_malone_status = None
                new_remote_importance = None
                new_malone_importance = None
                error = None
                oops_id = None

                # XXX: 2007-10-17 Graham Binns
                #      This nested set of try:excepts isn't really
                #      necessary and can be refactored out when bug
                #      136391 is dealt with.
                try:
                    new_remote_status = (
                        remotesystem.getRemoteStatus(remote_bug_id))
                    new_malone_status = self._convertRemoteStatus(
                        remotesystem, new_remote_status)
                    new_remote_importance = (
                        remotesystem.getRemoteImportance(remote_bug_id))
                    new_malone_importance = (
                        remotesystem.convertRemoteImportance(
                            new_remote_importance))
                except (InvalidBugId, BugNotFound, PrivateRemoteBug), ex:
                    error = get_bugwatcherrortype_for_error(ex)
                    message = error_type_messages.get(
                        error, error_type_message_default)
                    oops_id = self.warning(
                        message % {
                            'bug_id': remote_bug_id,
                            'base_url': remotesystem.baseurl,
                            'local_ids': local_ids,
                            },
                        properties=[
                            ('URL', remote_bug_url),
                            ('bug_id', remote_bug_id),
                            ('local_ids', local_ids),
                            ] + get_remote_system_oops_properties(remotesystem),
                        info=sys.exc_info())

                for bug_watch in bug_watches:
                    with self.transaction:
                        bug_watch.last_error_type = error
                        if new_malone_status is not None:
                            bug_watch.updateStatus(
                                new_remote_status, new_malone_status)
                        if new_malone_importance is not None:
                            bug_watch.updateImportance(
                                new_remote_importance, new_malone_importance)
                        # Only sync comments and backlink if the local
                        # bug isn't a duplicate, *and* if the bug
                        # watch is associated with a bug task. This
                        # helps us to avoid spamming upstream.
                        do_sync = (
                            bug_watch.bug.duplicateof is None and
                            len(bug_watch.bugtasks) > 0)

                    if do_sync:
                        if can_import_comments:
                            self.importBugComments(remotesystem, bug_watch)
                        if can_push_comments:
                            self.pushBugComments(remotesystem, bug_watch)
                        if ISupportsBackLinking.providedBy(remotesystem):
                            self.linkLaunchpadBug(remotesystem, bug_watch)

                    with self.transaction:
                        bug_watch.addActivity(
                            result=error, oops_id=oops_id)

            except (KeyboardInterrupt, SystemExit):
                # We should never catch KeyboardInterrupt or SystemExit.
                raise

            except Exception, error:
                # Send the error to the log.
                oops_id = self.error(
                    "Failure updating bug %r on %s (local bugs: %s)." %
                            (remote_bug_id, bug_tracker_url, local_ids),
                    properties=[
                        ('URL', remote_bug_url),
                        ('bug_id', remote_bug_id),
                        ('local_ids', local_ids)] +
                        get_remote_system_oops_properties(remotesystem))
                # We record errors against the bug watches and update
                # their lastchecked dates so that we don't try to
                # re-check them every time checkwatches runs.
                errortype = get_bugwatcherrortype_for_error(error)
                with self.transaction:
                    for bugwatch in bug_watches:
                        bugwatch.lastchecked = UTC_NOW
                        bug_watch.next_check = None
                        bugwatch.last_error_type = errortype
                        bug_watch.addActivity(
                            result=errortype, oops_id=oops_id)

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
        with self.transaction:
            local_bug_id = bug_watch.bug.id
            remote_bug_id = bug_watch.remotebug

        # Construct a list of the comment IDs we want to import; i.e.
        # those which we haven't already imported.
        all_comment_ids = external_bugtracker.getCommentIds(remote_bug_id)

        with self.transaction:
            comment_ids_to_import = [
                comment_id for comment_id in all_comment_ids
                if not bug_watch.hasComment(comment_id)]

        external_bugtracker.fetchComments(
            remote_bug_id, comment_ids_to_import)

        with self.transaction:
            previous_imported_comments = bug_watch.getImportedBugMessages()
            is_initial_import = previous_imported_comments.count() == 0
            imported_comments = []

            for comment_id in comment_ids_to_import:
                displayname, email = external_bugtracker.getPosterForComment(
                    remote_bug_id, comment_id)

                if displayname is None and email is None:
                    # If we don't have a displayname or an email address
                    # then we can't create a Launchpad Person as the author
                    # of this comment. We raise an OOPS and continue.
                    self.warning(
                        "Unable to import remote comment author. No email "
                        "address or display name found.",
                        get_remote_system_oops_properties(external_bugtracker),
                        sys.exc_info())
                    continue

                poster = bug_watch.bugtracker.ensurePersonForSelf(
                    displayname, email, PersonCreationRationale.BUGIMPORT,
                    "when importing comments for %s." % bug_watch.title)

                comment_message = external_bugtracker.getMessageForComment(
                    remote_bug_id, comment_id, poster)

                bug_message = bug_watch.addComment(
                    comment_id, comment_message)
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

            self.logger.info("Imported %(count)i comments for remote bug "
                "%(remotebug)s on %(bugtracker_url)s into Launchpad bug "
                "%(bug_id)s." %
                {'count': len(imported_comments),
                 'remotebug': remote_bug_id,
                 'bugtracker_url': external_bugtracker.baseurl,
                 'bug_id': local_bug_id})

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

        with self.transaction:
            local_bug_id = bug_watch.bug.id
            remote_bug_id = bug_watch.remotebug
            unpushed_comments = list(bug_watch.unpushed_comments)

        # Loop over the unpushed comments for the bug watch.
        # We only push those comments that haven't been pushed
        # already. We don't push any comments not associated with
        # the bug watch.
        for unpushed_comment in unpushed_comments:
            with self.transaction:
                message = unpushed_comment.message
                message_rfc822msgid = message.rfc822msgid
                # Format the comment so that it includes information
                # about the Launchpad bug.
                formatted_comment = self._formatRemoteComment(
                    external_bugtracker, bug_watch, message)

            remote_comment_id = (
                external_bugtracker.addRemoteComment(
                    remote_bug_id, formatted_comment,
                    message_rfc822msgid))

            assert remote_comment_id is not None, (
                "A remote_comment_id must be specified.")
            with self.transaction:
                unpushed_comment.remote_comment_id = remote_comment_id

            pushed_comments += 1

        if pushed_comments > 0:
            self.logger.info("Pushed %(count)i comments to remote bug "
                "%(remotebug)s on %(bugtracker_url)s from Launchpad bug "
                "%(bug_id)s" %
                {'count': pushed_comments,
                 'remotebug': remote_bug_id,
                 'bugtracker_url': external_bugtracker.baseurl,
                 'bug_id': local_bug_id})

    def linkLaunchpadBug(self, remotesystem, bug_watch):
        """Link a Launchpad bug to a given remote bug."""
        with self.transaction:
            local_bug_id = bug_watch.bug.id
            remote_bug_id = bug_watch.remotebug

        current_launchpad_id = remotesystem.getLaunchpadBugId(remote_bug_id)

        if current_launchpad_id is None:
            # If no bug is linked to the remote bug, link this one and
            # then stop.
            remotesystem.setLaunchpadBugId(remote_bug_id, local_bug_id)
            return

        elif current_launchpad_id == local_bug_id:
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
                with self.transaction:
                    other_launchpad_bug = getUtility(IBugSet).get(
                        current_launchpad_id)
                    other_bug_watch = other_launchpad_bug.getBugWatch(
                        bug_watch.bugtracker, remote_bug_id)
            except NotFoundError:
                # If we can't find the bug that's referenced by
                # current_launchpad_id we simply set other_bug_watch to
                # None so that the Launchpad ID of the remote bug can be
                # set correctly.
                other_bug_watch = None

            if other_bug_watch is None:
                remotesystem.setLaunchpadBugId(remote_bug_id, local_bug_id)


class BaseScheduler:
    """Run jobs according to a policy."""

    def schedule(self, func, *args, **kwargs):
        """Add a job to be run."""
        raise NotImplementedError(self.schedule)

    def run(self):
        """Run the jobs."""
        raise NotImplementedError(self.run)


class SerialScheduler(BaseScheduler):
    """Run jobs in order, one at a time."""

    def __init__(self):
        self._jobs = []

    def schedule(self, func, *args, **kwargs):
        self._jobs.append((func, args, kwargs))

    def run(self):
        jobs, self._jobs = self._jobs[:], []
        for (func, args, kwargs) in jobs:
            func(*args, **kwargs)


class TwistedThreadScheduler(BaseScheduler):
    """Run jobs in threads, chaperoned by Twisted."""

    def __init__(self, num_threads, install_signal_handlers=True):
        """Create a new `TwistedThreadScheduler`.

        :param num_threads: The number of threads to allocate to the
          thread pool.
        :type num_threads: int

        :param install_signal_handlers: Whether the Twisted reactor
          should install signal handlers or not. This is intented for
          testing - set to False to avoid layer violations - but may
          be useful in other situations.
        :type install_signal_handlers: bool
        """
        self._thread_pool = ThreadPool(0, num_threads)
        self._install_signal_handlers = install_signal_handlers
        self._jobs = []

    def schedule(self, func, *args, **kwargs):
        self._jobs.append(
            deferToThreadPool(
                reactor, self._thread_pool, func, *args, **kwargs))

    def run(self):
        jobs, self._jobs = self._jobs[:], []
        jobs_done = DeferredList(jobs)
        jobs_done.addBoth(lambda ignore: self._thread_pool.stop())
        jobs_done.addBoth(lambda ignore: reactor.stop())
        reactor.callWhenRunning(self._thread_pool.start)
        reactor.run(self._install_signal_handlers)


class CheckWatchesCronScript(LaunchpadCronScript):

    def add_my_options(self):
        """See `LaunchpadScript`."""
        self.parser.add_option(
            '-t', '--bug-tracker', action='append',
            dest='bug_trackers', metavar="BUG_TRACKER",
            help="Only check a given bug tracker. Specifying more than "
                "one bugtracker using this option will check all the "
                "bugtrackers specified.")
        self.parser.add_option(
            '-b', '--batch-size', action='store', type=int, dest='batch_size',
            help="Set the number of watches to be checked per bug "
                 "tracker in this run. If BATCH_SIZE is 0, all watches "
                 "on the bug tracker that are eligible for checking will "
                 "be checked.")
        self.parser.add_option(
            '--reset', action='store_true', dest='update_all',
            help="Update all the watches on the bug tracker, regardless of "
                 "whether or not they need checking.")
        self.parser.add_option(
            '--jobs', action='store', type=int, dest='jobs', default=1,
            help=("The number of simulataneous jobs to run, %default by "
                  "default."))

    def main(self):
        start_time = time.time()

        updater = BugWatchUpdater(self.txn, self.logger)

        if self.options.update_all and len(self.options.bug_trackers) > 0:
            # The user has requested that we update *all* the watches
            # for these bugtrackers
            for bug_tracker in self.options.bug_trackers:
                updater.forceUpdateAll(bug_tracker, self.options.batch_size)
        else:
            # Otherwise we just update those watches that need updating,
            # and we let the BugWatchUpdater decide which those are.
            if self.options.jobs <= 1:
                # Use the default scheduler.
                scheduler = None
            else:
                # Run jobs in parallel.
                scheduler = TwistedThreadScheduler(self.options.jobs)
            updater.updateBugTrackers(
                self.options.bug_trackers,
                self.options.batch_size,
                scheduler)

        run_time = time.time() - start_time
        self.logger.info("Time for this run: %.3f seconds." % run_time)
