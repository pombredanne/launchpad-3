# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Debbugs ExternalBugTracker utility."""

__metaclass__ = type
__all__ = [
    'DebBugs',
    'DebBugsDatabaseNotFound'
    ]

from datetime import datetime
import email
import os.path

from email.Utils import parseaddr

from zope.component import getUtility
from zope.interface import implements

import pytz

from canonical.config import config
from canonical.database.sqlbase import commit
from canonical.launchpad.components.externalbugtracker import (
    BugNotFound, BugTrackerConnectError, ExternalBugTracker,
    InvalidBugId, UnknownRemoteStatusError)
from canonical.launchpad.interfaces import (
    BugTaskImportance, BugTaskStatus, IMessageSet, ISupportsBugImport,
    ISupportsCommentImport, UNKNOWN_REMOTE_IMPORTANCE)
from canonical.launchpad.scripts import debbugs


debbugsstatusmap = {'open':      BugTaskStatus.NEW,
                    'forwarded': BugTaskStatus.CONFIRMED,
                    'done':      BugTaskStatus.FIXRELEASED}


class DebBugsDatabaseNotFound(BugTrackerConnectError):
    """The Debian bug database was not found."""


class DebBugs(ExternalBugTracker):
    """A class that deals with communications with a debbugs db."""

    implements(ISupportsBugImport, ISupportsCommentImport)

    # We don't support different versions of debbugs.
    version = None
    debbugs_pl = os.path.join(
        os.path.dirname(debbugs.__file__), 'debbugs-log.pl')

    def __init__(self, baseurl, db_location=None):
        super(DebBugs, self).__init__(baseurl)
        if db_location is None:
            self.db_location = config.malone.debbugs_db_location
        else:
            self.db_location = db_location

        if not os.path.exists(os.path.join(self.db_location, 'db-h')):
            raise DebBugsDatabaseNotFound(
                self.db_location, '"db-h" not found.')

        # The debbugs database is split in two parts: a current
        # database, which is kept under the 'db-h' directory, and
        # the archived database, which is kept under 'archive'. The
        # archived database is used as a fallback, as you can see in
        # getRemoteStatus
        self.debbugs_db = debbugs.Database(
            self.db_location, self.debbugs_pl)
        if os.path.exists(os.path.join(self.db_location, 'archive')):
            self.debbugs_db_archive = debbugs.Database(
                self.db_location, self.debbugs_pl, subdir="archive")

    def getCurrentDBTime(self):
        """See `IExternalBugTracker`."""
        # We don't know the exact time for the Debbugs server, but we
        # trust it being correct.
        return datetime.now(pytz.timezone('UTC'))


    def initializeRemoteBugDB(self, bug_ids):
        """See `ExternalBugTracker`.

        This method is overridden (and left empty) here to avoid breakage when
        the continuous bug-watch checking spec is implemented.
        """

    def convertRemoteImportance(self, remote_importance):
        """See `ExternalBugTracker`.

        This method is implemented here as a stub to ensure that
        existing functionality is preserved. As a result,
        BugTaskImportance.UNKNOWN will always be returned.
        """
        return BugTaskImportance.UNKNOWN

    def convertRemoteStatus(self, remote_status):
        """Convert a debbugs status to a Malone status.

        A debbugs status consists of either two or three parts,
        separated with space; the status and severity, followed by
        optional tags. The tags are also separated with a space
        character.
        """
        parts = remote_status.split(' ')
        if len(parts) < 2:
            raise UnknownRemoteStatusError()

        status = parts[0]
        severity = parts[1]
        tags = parts[2:]

        # For the moment we convert only the status, not the severity.
        try:
            malone_status = debbugsstatusmap[status]
        except KeyError:
            raise UnknownRemoteStatusError()
        if status == 'open':
            confirmed_tags = [
                'help', 'confirmed', 'upstream', 'fixed-upstream']
            fix_committed_tags = ['pending', 'fixed', 'fixed-in-experimental']
            if 'moreinfo' in tags:
                malone_status = BugTaskStatus.INCOMPLETE
            for confirmed_tag in confirmed_tags:
                if confirmed_tag in tags:
                    malone_status = BugTaskStatus.CONFIRMED
                    break
            for fix_committed_tag in fix_committed_tags:
                if fix_committed_tag in tags:
                    malone_status = BugTaskStatus.FIXCOMMITTED
                    break
            if 'wontfix' in tags:
                malone_status = BugTaskStatus.WONTFIX

        return malone_status

    def _findBug(self, bug_id):
        if not bug_id.isdigit():
            raise InvalidBugId(
                "Debbugs bug number not an integer: %s" % bug_id)
        try:
            debian_bug = self.debbugs_db[int(bug_id)]
        except KeyError:
            # If we couldn't find it in the main database, there's
            # always the archive.
            try:
                debian_bug = self.debbugs_db_archive[int(bug_id)]
            except KeyError:
                raise BugNotFound(bug_id)

        return debian_bug

    def _loadLog(self, debian_bug):
        """Load the debbugs comment log for a given bug.

        This method is analogous to _findBug() in that if the comment
        log cannot be loaded from the main database it will attempt to
        load the log from the archive database.

        If no comment log can be found, a debbugs.LogParseFailed error
        will be raised.
        """
        # If we can't find the log in the main database we try the
        # archive.
        try:
            self.debbugs_db.load_log(debian_bug)
        except debbugs.LogParseFailed:
            # If there is no log for this bug in the archive a
            # LogParseFailed error will be raised. However, we let that
            # propagate upwards since we need to make the callsite deal
            # with the fact that there's no log to parse.
            self.debbugs_db_archive.load_log(debian_bug)

    def getRemoteImportance(self, bug_id):
        """See `ExternalBugTracker`.

        This method is implemented here as a stub to ensure that
        existing functionality is preserved. As a result,
        UNKNOWN_REMOTE_IMPORTANCE will always be returned.
        """
        return UNKNOWN_REMOTE_IMPORTANCE

    def getRemoteStatus(self, bug_id):
        """See ExternalBugTracker."""
        debian_bug = self._findBug(bug_id)
        if not debian_bug.severity:
            # 'normal' is the default severity in debbugs.
            severity = 'normal'
        else:
            severity = debian_bug.severity
        new_remote_status = ' '.join(
            [debian_bug.status, severity] + debian_bug.tags)
        return new_remote_status

    def getBugReporter(self, remote_bug):
        """See ISupportsBugImport."""
        debian_bug = self._findBug(remote_bug)
        reporter_name, reporter_email = parseaddr(debian_bug.originator)
        return reporter_name, reporter_email

    def getBugTargetName(self, remote_bug):
        """See ISupportsBugImport."""
        debian_bug = self._findBug(remote_bug)
        return debian_bug.package

    def getBugSummaryAndDescription(self, remote_bug):
        """See ISupportsBugImport."""
        debian_bug = self._findBug(remote_bug)
        return debian_bug.subject, debian_bug.description

    def getCommentIds(self, bug_watch):
        """See `ISupportsCommentImport`."""
        debian_bug = self._findBug(bug_watch.remotebug)
        self._loadLog(debian_bug)

        comment_ids = []
        for comment in debian_bug.comments:
            parsed_comment = email.message_from_string(comment)
            comment_ids.append(parsed_comment['message-id'])

        return comment_ids

    def getPosterForComment(self, bug_watch, comment_id):
        """See `ISupportsCommentImport`."""
        debian_bug = self._findBug(bug_watch.remotebug)
        self._loadLog(debian_bug)

        for comment in debian_bug.comments:
            parsed_comment = email.message_from_string(comment)
            if parsed_comment['message-id'] == comment_id:
                return parseaddr(parsed_comment['from'])

    def getMessageForComment(self, bug_watch, comment_id, poster):
        """See `ISupportsCommentImport`."""
        debian_bug = self._findBug(bug_watch.remotebug)
        self._loadLog(debian_bug)

        for comment in debian_bug.comments:
            parsed_comment = email.message_from_string(comment)
            if parsed_comment['message-id'] == comment_id:
                message = getUtility(IMessageSet).fromEmail(comment, poster,
                    parsed_message=parsed_comment)

                commit()
                return message

