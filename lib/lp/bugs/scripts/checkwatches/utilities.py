# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Utility functions for checkwatches."""

__metaclass__ = type
__all__ = [
    'get_bugwatcherrortype_for_error',
    'get_remote_system_oops_properties',
    ]

import socket

from lp.bugs.externalbugtracker import (
    BugNotFound, BugTrackerConnectError, InvalidBugId, PrivateRemoteBug,
    UnknownBugTrackerTypeError, UnparseableBugData,
    UnparseableBugTrackerVersion, UnsupportedBugTrackerVersion)

from lp.bugs.interfaces.bugwatch import BugWatchActivityStatus


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
