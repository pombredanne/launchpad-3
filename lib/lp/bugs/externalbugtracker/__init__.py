# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""__init__ module for the externalbugtracker package."""

__metaclass__ = type
__all__ = [
    'BATCH_SIZE_UNLIMITED',
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
    'UnparsableBugData',
    'UnparsableBugTrackerVersion',
    'UnsupportedBugTrackerVersion',
    'get_external_bugtracker',
    ]

from lp.bugs.externalbugtracker.base import (
    BATCH_SIZE_UNLIMITED,
    BugNotFound,
    BugTrackerConnectError,
    BugWatchUpdateError,
    BugWatchUpdateWarning,
    ExternalBugTracker,
    InvalidBugId,
    LookupTree,
    PrivateRemoteBug,
    UnknownBugTrackerTypeError,
    UnknownRemoteStatusError,
    UnparsableBugData,
    UnparsableBugTrackerVersion,
    UnsupportedBugTrackerVersion,
    )
from lp.bugs.externalbugtracker.bugzilla import Bugzilla
from lp.bugs.externalbugtracker.debbugs import (
    DebBugs,
    DebBugsDatabaseNotFound,
    )
from lp.bugs.externalbugtracker.mantis import (
    Mantis,
    MantisLoginHandler,
    )
from lp.bugs.externalbugtracker.roundup import Roundup
from lp.bugs.externalbugtracker.rt import RequestTracker
from lp.bugs.externalbugtracker.sourceforge import SourceForge
from lp.bugs.externalbugtracker.trac import Trac
from lp.bugs.interfaces.bugtracker import BugTrackerType


BUG_TRACKER_CLASSES = {
    BugTrackerType.BUGZILLA: Bugzilla,
    BugTrackerType.DEBBUGS: DebBugs,
    BugTrackerType.MANTIS: Mantis,
    BugTrackerType.TRAC: Trac,
    BugTrackerType.ROUNDUP: Roundup,
    BugTrackerType.RT: RequestTracker,
    BugTrackerType.SOURCEFORGE: SourceForge,
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
