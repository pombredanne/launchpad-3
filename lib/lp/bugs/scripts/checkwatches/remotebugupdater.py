# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Classes and logic for the remote bug updater."""

from __future__ import with_statement

__metaclass__ = type
__all__ = [
    'RemoteBugUpdater',
    ]

import socket
import sys

from zope.component import getUtility

from canonical.database.constants import UTC_NOW

from lp.bugs.externalbugtracker import (
    BugNotFound, BugTrackerConnectError, BugWatchUpdateError,
    InvalidBugId, PrivateRemoteBug, UnknownBugTrackerTypeError,
    UnknownRemoteStatusError, UnparseableBugData,
    UnparseableBugTrackerVersion, UnsupportedBugTrackerVersion)

from lp.bugs.interfaces.bugwatch import BugWatchActivityStatus, IBugWatchSet
from lp.bugs.scripts.checkwatches.base import WorkingBase
from lp.bugs.scripts.checkwatches.bugwatchupdater import BugWatchUpdater
from lp.bugs.scripts.checkwatches.utilities import (
    get_bugwatcherrortype_for_error, get_remote_system_oops_properties)


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


class RemoteBugUpdater(WorkingBase):

    def __init__(self, parent, external_bugtracker, remote_bug,
                 bug_watch_ids, unmodified_remote_ids):
        self.initFromParent(parent)
        self.external_bugtracker = external_bugtracker
        self.bug_tracker_url = external_bugtracker.baseurl
        self.remote_bug = remote_bug
        self.bug_watch_ids = bug_watch_ids
        self.unmodified_remote_ids = unmodified_remote_ids

        self.error_type_messages = {
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
        self.error_type_message_default = (
            "remote bug: %(bug_id)r; "
            "base url: %(base_url)s; "
            "local bugs: %(local_ids)s"
            )

    def _getBugWatchesForRemoteBug(self):
        """Return a list of bug watches for the current remote bug.

        The returned watches will all be members of `self.bug_watch_ids`.

        This method exists primarily to be overridden during testing.
        """
        return list(
            getUtility(IBugWatchSet).getBugWatchesForRemoteBug(
                self.remote_bug, self.bug_watch_ids))

    def updateRemoteBug(self, can_import_comments, can_push_comments,
                        can_back_link):
        # Avoid circular imports
        with self.transaction:
            bug_watches = self._getBugWatchesForRemoteBug()
            # If there aren't any bug watches for this remote bug,
            # just log a warning and carry on.
            if len(bug_watches) == 0:
                self.warning(
                    "Spurious remote bug ID: No watches found for "
                    "remote bug %s on %s" % (
                        self.remote_bug, self.external_bugtracker.baseurl))
                return
            # Mark them all as checked.
            for bug_watch in bug_watches:
                bug_watch.lastchecked = UTC_NOW
                bug_watch.next_check = None
            # Next if this one is definitely unmodified.
            if self.remote_bug in self.unmodified_remote_ids:
                return
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
                    self.external_bugtracker.getRemoteStatus(
                        self.remote_bug))
                new_malone_status = self._convertRemoteStatus(
                    self.external_bugtracker, new_remote_status)
                new_remote_importance = (
                    self.external_bugtracker.getRemoteImportance(
                        self.remote_bug))
                new_malone_importance = (
                    self.external_bugtracker.convertRemoteImportance(
                        new_remote_importance))
            except (InvalidBugId, BugNotFound, PrivateRemoteBug), ex:
                error = get_bugwatcherrortype_for_error(ex)
                message = self.error_type_messages.get(
                    error, self.error_type_message_default)
                oops_id = self.warning(
                    message % {
                        'bug_id': self.remote_bug,
                        'base_url': self.external_bugtracker.baseurl,
                        'local_ids': local_ids,
                        },
                    properties=[
                        ('URL', remote_bug_url),
                        ('bug_id', self.remote_bug),
                        ('local_ids', local_ids),
                        ] + get_remote_system_oops_properties(
                            self.external_bugtracker),
                    info=sys.exc_info())

            for bug_watch in bug_watches:
                bug_watch_updater = BugWatchUpdater(
                    self, bug_watch, self.external_bugtracker)

                bug_watch_updater.updateBugWatch(
                    new_remote_status, new_malone_status,
                    new_remote_importance, new_malone_importance,
                    can_import_comments, can_push_comments,
                    can_back_link, error, oops_id)

        except (KeyboardInterrupt, SystemExit):
            # We should never catch KeyboardInterrupt or SystemExit.
            raise

        except Exception, error:
            # Send the error to the log.
            oops_id = self.error(
                "Failure updating bug %r on %s (local bugs: %s)." %
                        (self.remote_bug, self.bug_tracker_url, local_ids),
                properties=[
                    ('URL', remote_bug_url),
                    ('bug_id', self.remote_bug),
                    ('local_ids', local_ids)] +
                    get_remote_system_oops_properties(
                        self.external_bugtracker))
            # We record errors against the bug watches and update
            # their lastchecked dates so that we don't try to
            # re-check them every time checkwatches runs.
            error_type = get_bugwatcherrortype_for_error(error)
            with self.transaction:
                for bug_watch in bug_watches:
                    bug_watch.lastchecked = UTC_NOW
                    bug_watch.next_check = None
                    bug_watch.last_error_type = error_type
                    bug_watch.addActivity(
                        result=error_type, oops_id=oops_id)
