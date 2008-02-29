# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces declarations for external bugtrackers."""

__metaclass__ = type

__all__ = [
    'IExternalBugTracker',
    'ISupportsCommentImport',
    'ISupportsBugImport',
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


class IExternalBugTracker(Interface):
    """A class used to talk with an external bug tracker."""

    def convertRemoteStatus(remote_status):
        """Convert a remote status string to a BugTaskStatus item."""

    def convertRemoteImportance(remote_importance):
        """Convert a remote importance to a BugTaskImportance item."""


class ISupportsCommentImport(IExternalBugTracker):
    """A an external bug tracker that supports comment imports."""


class ISupportsBugImport(IExternalBugTracker):
    """A an external bug tracker that supports bug imports."""

    def getReporter(remote_bug):
        """Return the person who submitted the given bug.

        A tuple of (display name, email) is returned.
        """

    def getSummaryAndDescription(remote_bug):
        """Return a tuple of summary and description for the given bug."""

    def getTarget(self, remote_bug):
        """Return the specific target of the bug.

        Return None if no target can be determined.
        """
