# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces declarations for external bugtrackers."""

__metaclass__ = type

__all__ = [
    'IExternalBugTracker',
    'IExternalBugTrackerTokenAPI',
    'ISupportsBackLinking',
    'ISupportsBugImport',
    'ISupportsCommentImport',
    'ISupportsCommentPushing',
    'UNKNOWN_REMOTE_IMPORTANCE',
    'UNKNOWN_REMOTE_STATUS',
    ]

from zope.interface import Interface

# This is a text string which indicates that the remote status is
# unknown for some reason.
# XXX: Bjorn Tillenius 2006-04-06:
#      We should store the actual reason for the error somewhere. This
#      would allow us to get rid of these text constants.
UNKNOWN_REMOTE_STATUS = 'UNKNOWN'
UNKNOWN_REMOTE_IMPORTANCE = 'UNKNOWN'


class IExternalBugTrackerTokenAPI(Interface):
    """A class used to generate external bugtracker `LoginToken`s."""

    def newBugTrackerToken():
        """Create a new bugtracker `LoginToken` and return its ID."""


class IExternalBugTracker(Interface):
    """A class used to talk with an external bug tracker."""

    def getExternalBugTrackerToUse():
        """Return the `ExternalBugTracker` instance to use.

        Probe the remote bug tracker and choose the right
        `ExternalBugTracker` instance to use further on.
        """

    def getCurrentDBTime():
        """Return the current time of the bug tracker's DB server.

        The current time will be returned as a timezone-aware datetime.
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

    def getRemoteProduct(remote_bug):
        """Return the remote product for a given remote bug.

        :param remote_bug: The ID of the remote bug for which to return
            the remote product.
        :return: The remote product for `remote_bug`. If no remote
            product is recorded for `remote_bug` return None.
        :raise BugNotFound: If `remote_bug` doesn't exist for the bug
            tracker.
        """


class ISupportsCommentImport(IExternalBugTracker):
    """An external bug tracker that supports comment imports."""

    def fetchComments(bug_watch, comment_ids):
        """Load a given set of remote comments, ready for parsing.

        :param bug_watch: The bug watch for which to fetch the comments.
        :param comment_ids: A list of the IDs of the comments to load.
        """

    def getCommentIds(bug_watch):
        """Return all the comment IDs for a given remote bug.

        :param bug_watch: An `IBugWatch` pointing to the remote bug from
            which comments should be imported.
        :return: A list of strings, each of which is the ID of one
            comment on the remote bug.
        """

    def getPosterForComment(bug_watch, comment_id):
        """Return a tuple of (name, emailaddress) for a comment's poster.

        :param bug_watch: An `IBugWatch` pointing to the remote bug from
            which comments should be imported.
        :param comment_id: A string representing the remote comment ID
            from which the poster's details should be extracted.
        """

    def getMessageForComment(bug_watch, comment_id, poster):
        """Return an `IMessage` instance for a comment.

        :param bug_watch: An `IBugWatch` pointing to the remote bug from
            which comments should be imported.
        :param comment_id: A string representing the remote comment ID
            from which the returned `IMessage` should be created.
        """


class ISupportsBugImport(IExternalBugTracker):
    """An external bug tracker that supports bug imports."""

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


class ISupportsCommentPushing(IExternalBugTracker):
    """An external bug tracker that can push comments to the remote tracker.
    """

    def addRemoteComment(remote_bug, comment_body, rfc822msgid):
        """Push a comment to the remote bug.

        :param remote_bug: The ID of the bug on the remote tracker to
            which the comment should be attached.
        :param comment_body: The body of the comment to push.
        :param rfc822msgid: The RFC-822 message ID of the comment in
            Launchpad.
        :return: The ID assigned to the comment by the remote bugtracker
            as a string.
        """


class ISupportsBackLinking(IExternalBugTracker):

    def getLaunchpadBugId(remote_bug):
        """Return a Launchpad bug ID for a given remote bug.

        :param remote_bug: The ID of the bug on the remote tracker from
            which to get the Launchpad bug ID.

        The bug ID returned is that which the remote tracker has a
        record of after setLaunchpadBugId() has been called.

        Return None if there is no recorded Launchpad bug ID for
        `remote_bug`.
        """

    def setLaunchpadBugId(remote_bug, launchpad_bug_id):
        """Set the Launchpad bug ID for a bug on the remote bug tracker.

        :param remote_bug: The ID of the bug on the remote tracker on
            which to set the Launchpad bug ID.
        :param launchpad_bug_id: The ID of the Launchpad bug that's
            watching the remote bug.
        """

