# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Classes and logic for the checkwatches BugWatchUpdater."""

from __future__ import with_statement

__metaclass__ = type
__all__ = []

import sys

from zope.component import getUtility
from zope.event import notify

from canonical.database.sqlbase import flush_database_updates

from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.interfaces.launchpad import (
    ILaunchpadCelebrities, NotFoundError)
from canonical.launchpad.webapp.publisher import canonical_url

from lazr.lifecycle.event import ObjectCreatedEvent

from lp.bugs.interfaces.bug import CreateBugParams, IBugSet
from lp.bugs.interfaces.bugwatch import IBugWatchSet
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.message import IMessageSet
from lp.registry.interfaces.person import IPersonSet, PersonCreationRationale


class BugWatchUpdater:
    """Handles the updating of a single BugWatch for checkwatches."""

    def __init__(self, bug_watch):
        self.bug_watch = bug_watch

    def updateBugWatch(self):
        """Update the BugWatch."""
        with self.transaction:
            bug_watch.last_error_type = error
            if new_malone_status is not None:
                bug_watch.updateStatus(
                    new_remote_status, new_malone_status)
            if new_malone_importance is not None:
                bug_watch.updateImportance(
                    new_remote_importance, new_malone_importance)
            # Only sync comments and backlink if there was no
            # earlier error, the local bug isn't a duplicate,
            # *and* if the bug watch is associated with a bug
            # task. This helps us to avoid spamming upstream.
            do_sync = (
                error is None and
                bug_watch.bug.duplicateof is None and
                len(bug_watch.bugtasks) > 0
                )

        # XXX: Gavin Panella 2010-04-19 bug=509223:
        # Exception handling is all wrong! If any of these
        # throw an exception, *all* the watches in
        # bug_watches, even those that have not errored,
        # will have negative activity added.
        if do_sync:
            if can_import_comments:
                self.importBugComments(remotesystem, bug_watch)
            if can_push_comments:
                self.pushBugComments(remotesystem, bug_watch)
            if can_back_link:
                self.linkLaunchpadBug(remotesystem, bug_watch)

        with self.transaction:
            bug_watch.addActivity(
                result=error, oops_id=oops_id)


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
            local_bug_url = canonical_url(bug_watch.bug)
            remote_bug_id = bug_watch.remotebug

        current_launchpad_id = remotesystem.getLaunchpadBugId(remote_bug_id)

        if current_launchpad_id is None:
            # If no bug is linked to the remote bug, link this one and
            # then stop.
            remotesystem.setLaunchpadBugId(
                remote_bug_id, local_bug_id, local_bug_url)
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
                remotesystem.setLaunchpadBugId(
                    remote_bug_id, local_bug_id, local_bug_url)

