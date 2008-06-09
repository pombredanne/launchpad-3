# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0401

"""__init__ module for the externalbugtracker package."""

__metaclass__ = type
__all__ = [
    'get_bugwatcherrortype_for_error',
    'get_external_bugtracker',
    'BugNotFound',
    'BugTrackerConnectError',
    'BugWatchUpdateError',
    'BugWatchUpdateWarning',
    'Bugzilla',
    'DebBugs',
    'DebBugsDatabaseNotFound',
    'ExternalBugTracker',
    'InvalidBugId',
    'LookupTree',
    'Mantis',
    'MantisLoginHandler',
    'PrivateRemoteBug',
    'RequestTracker',
    'Roundup',
    'SourceForge',
    'Trac',
    'UnknownBugTrackerTypeError',
    'UnknownRemoteStatusError',
    'UnparseableBugData',
    'UnparseableBugTrackerVersion',
    'UnsupportedBugTrackerVersion',
    ]

from canonical.launchpad.components.externalbugtracker.base import *
from canonical.launchpad.components.externalbugtracker.bugzilla import *
from canonical.launchpad.components.externalbugtracker.debbugs import *
from canonical.launchpad.components.externalbugtracker.mantis import *
from canonical.launchpad.components.externalbugtracker.roundup import *
from canonical.launchpad.components.externalbugtracker.sourceforge import *
from canonical.launchpad.components.externalbugtracker.rt import *
from canonical.launchpad.components.externalbugtracker.trac import *
from canonical.launchpad.interfaces import BugTrackerType


BUG_TRACKER_CLASSES = {
    BugTrackerType.BUGZILLA: Bugzilla,
    BugTrackerType.DEBBUGS: DebBugs,
    BugTrackerType.MANTIS: Mantis,
    BugTrackerType.TRAC: Trac,
    BugTrackerType.ROUNDUP: Roundup,
    BugTrackerType.RT: RequestTracker,
    BugTrackerType.SOURCEFORGE: SourceForge
    }


def get_external_bugtracker(bugtracker):
    """Return an `ExternalBugTracker` for bugtracker."""
    bugtrackertype = bugtracker.bugtrackertype
    bugtracker_class = BUG_TRACKER_CLASSES.get(bugtracker.bugtrackertype)
    if bugtracker_class is not None:
        return bugtracker_class(bugtracker.baseurl)
    else:
        raise UnknownBugTrackerTypeError(bugtrackertype.name,
            bugtracker.name)
