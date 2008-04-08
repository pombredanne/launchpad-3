# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces declarations for external bugtrackers."""

__metaclass__ = type

__all__ = [
    'IExternalBugTracker',
    'IExternalBugTrackerTokenAPI',
    'ISupportsCommentImport',
    'ISupportsBugImport',
    'UNKNOWN_REMOTE_IMPORTANCE',
    'UNKNOWN_REMOTE_STATUS',
    ]

from zope.interface import Interface

from canonical.launchpad.webapp.interfaces import ILaunchpadApplication

# This is a text string which indicates that the remote status is
# unknown for some reason.
# XXX: Bjorn Tillenius 2006-04-06:
#      We should store the actual reason for the error somewhere. This
#      would allow us to get rid of these text constants.
UNKNOWN_REMOTE_STATUS = 'UNKNOWN'
UNKNOWN_REMOTE_IMPORTANCE = 'UNKNOWN'


class IExternalBugTrackerTokenAPI(Interface):
    """A class used to generate external bugtracker `LoginToken`s."""

    def newToken():
        """Create a new bugtracker `LoginToken` and return its ID."""


class IExternalBugTracker(Interface):
    """A class used to talk with an external bug tracker."""

    def getCurrentDBTime():
        """Return the current time of the bug tracker's DB server.

        The local time should be returned, as a timezone-aware datetime
        instance.
        """

    def getModifiedRemoteBugs(remote_bug_ids, last_checked):
        """Return the bug ids that have been modified.

        Return all ids if the modified bugs can't be determined.
        """

    def initializeRemoteBugDB(remote_bug_ids):
        """Do any initialization before each bug watch is updated."""

    def convertRemoteStatus(remote_status):
        """Convert a remote status string to a BugTaskStatus item."""

    def convertRemoteImportance(remote_importance):
        """Convert a remote importance to a BugTaskImportance item."""


class ISupportsCommentImport(IExternalBugTracker):
    """A an external bug tracker that supports comment imports."""

    def getCommentIds(bug_watch):
        """Return all the comment IDs for a given remote bug."""

    def getPosterForComment(bug_watch, comment_id):
        """Return a tuple of (name, emailaddress) for a comment's poster."""

    def getMessageForComment(bug_watch, comment_id, poster):
        """Return an `IMessage` instance for a comment."""


class ISupportsBugImport(IExternalBugTracker):
    """A an external bug tracker that supports bug imports."""

    def getBugReporter(remote_bug):
        """Return the person who submitted the given bug.

        A tuple of (display name, email) is returned.
        """

    def getBugSummaryAndDescription(remote_bug):
        """Return a tuple of summary and description for the given bug."""

    def getBugTargetName(remote_bug):
        """Return the specific target name of the bug.

        Return None if no target can be determined.
        """
