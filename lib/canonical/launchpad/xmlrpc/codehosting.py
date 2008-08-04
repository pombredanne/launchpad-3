# Copyright 2007 Canonical Ltd.  All rights reserved.

"""The branch details XML-RPC API."""

__metaclass__ = type
__all__ = [
    'BranchDetailsStorageAPI',
    ]

import datetime

import pytz

from zope.component import getUtility
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.branch import IBranchSet
from canonical.launchpad.interfaces.codehosting import (
    IBranchDetailsStorage)
from canonical.launchpad.interfaces.scriptactivity import IScriptActivitySet
from canonical.launchpad.webapp import LaunchpadXMLRPCView


UTC = pytz.timezone('UTC')


# XXX:
# - removeSecurityProxy still needed?
# - branchID -> branch_id
class BranchDetailsStorageAPI(LaunchpadXMLRPCView):
    """See `IBranchDetailsStorage`."""

    implements(IBranchDetailsStorage)

    def getBranchPullQueue(self, branch_type):
        """See `IBranchDetailsStorage`."""
        return []

    def mirrorComplete(self, branchID, lastRevisionID):
        """See `IBranchDetailsStorage`."""
        branch = getUtility(IBranchSet).get(branchID)
        if branch is None:
            return False
        # See comment in startMirroring.
        removeSecurityProxy(branch).mirrorComplete(lastRevisionID)
        return True

    def mirrorFailed(self, branchID, reason):
        """See `IBranchDetailsStorage`."""
        branch = getUtility(IBranchSet).get(branchID)
        if branch is None:
            return False
        # See comment in startMirroring.
        removeSecurityProxy(branch).mirrorFailed(reason)
        return True

    def recordSuccess(self, name, hostname, started_tuple, completed_tuple):
        """See `IBranchDetailsStorage`."""
        date_started = datetime_from_tuple(started_tuple)
        date_completed = datetime_from_tuple(completed_tuple)
        getUtility(IScriptActivitySet).recordSuccess(
            name=name, date_started=date_started,
            date_completed=date_completed, hostname=hostname)
        return True

    def startMirroring(self, branchID):
        """See `IBranchDetailsStorage`."""
        branch = getUtility(IBranchSet).get(branchID)
        if branch is None:
            return False
        # The puller runs as no user and may pull private branches. We need to
        # bypass Zope's security proxy to set the mirroring information.
        removeSecurityProxy(branch).startMirroring()
        return True


def datetime_from_tuple(time_tuple):
    """Create a datetime from a sequence that quacks like time.struct_time.

    The tm_isdst is (index 8) is ignored. The created datetime uses
    tzinfo=UTC.
    """
    [year, month, day, hour, minute, second, unused, unused, unused] = (
        time_tuple)
    return datetime.datetime(
        year, month, day, hour, minute, second, tzinfo=UTC)
