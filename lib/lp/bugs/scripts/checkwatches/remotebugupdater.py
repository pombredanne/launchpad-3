# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Classes and logic for the remote bug updater."""

from __future__ import with_statement

__metaclass__ = type
__all__ = []


from lp.bugs.scripts.checkwatches.base import WorkingBase


class RemoteBugUpdater(WorkingBase):

    def __init__(self, parent, remote_bug):
        self.initFromParent(parent)
        self.remote_bug = remote_bug

    def updateRemoteBug(self):
        with self.transaction:
            bug_watches = self._getBugWatchesForRemoteBug(
                self.remote_bug, bug_watch_ids)
            # If there aren't any bug watches for this remote bug,
            # just log a warning and carry on.
            if len(bug_watches) == 0:
                self.warning(
                    "Spurious remote bug ID: No watches found for "
                    "remote bug %s on %s" % (
                        self.remote_bug, remotesystem.baseurl))
                continue
            # Mark them all as checked.
            for bug_watch in bug_watches:
                bug_watch.lastchecked = UTC_NOW
                bug_watch.next_check = None
            # Next if this one is definitely unmodified.
            if self.remote_bug in unmodified_remote_ids:
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
                    remotesystem.getRemoteStatus(self.remote_bug))
                new_malone_status = self._convertRemoteStatus(
                    remotesystem, new_remote_status)
                new_remote_importance = (
                    remotesystem.getRemoteImportance(self.remote_bug))
                new_malone_importance = (
                    remotesystem.convertRemoteImportance(
                        new_remote_importance))
            except (InvalidBugId, BugNotFound, PrivateRemoteBug), ex:
                error = get_bugwatcherrortype_for_error(ex)
                message = error_type_messages.get(
                    error, error_type_message_default)
                oops_id = self.warning(
                    message % {
                        'bug_id': self.remote_bug,
                        'base_url': remotesystem.baseurl,
                        'local_ids': local_ids,
                        },
                    properties=[
                        ('URL', remote_bug_url),
                        ('bug_id', self.remote_bug),
                        ('local_ids', local_ids),
                        ] + get_remote_system_oops_properties(
                            remotesystem),
                    info=sys.exc_info())

            for bug_watch in bug_watches:
                bug_watch_updater = BugWatchUpdater(
                    self, bug_watch, remotesystem)

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
                        (self.remote_bug, bug_tracker_url, local_ids),
                properties=[
                    ('URL', remote_bug_url),
                    ('bug_id', self.remote_bug),
                    ('local_ids', local_ids)] +
                    get_remote_system_oops_properties(remotesystem))
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
