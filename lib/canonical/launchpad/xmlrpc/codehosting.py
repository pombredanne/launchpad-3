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

from canonical.launchpad.interfaces.branch import (
    BranchType, IBranchSet, UnknownBranchTypeError)
from canonical.launchpad.interfaces.codehosting import (
    IBranchDetailsStorage)
from canonical.launchpad.interfaces.scriptactivity import IScriptActivitySet
from canonical.launchpad.webapp import LaunchpadXMLRPCView


UTC = pytz.timezone('UTC')


class BranchDetailsStorageAPI(LaunchpadXMLRPCView):
    """See `IBranchDetailsStorage`."""

    implements(IBranchDetailsStorage)

    def _getBranchPullInfo(self, branch):
        """Return information the branch puller needs to pull this branch.

        This is outside of the IBranch interface so that the authserver can
        access the information without logging in as a particular user.

        :return: (id, url, unique_name), where `id` is the branch database ID,
            `url` is the URL to pull from and `unique_name` is the
            `unique_name` property without the initial '~'.
        """
        branch = removeSecurityProxy(branch)
        if branch.branch_type == BranchType.REMOTE:
            raise AssertionError(
                'Remote branches should never be in the pull queue.')
        return (branch.id, branch.getPullURL(), branch.unique_name)

    def getBranchPullQueue(self, branch_type):
        """See `IBranchDetailsStorage`."""
        try:
            branch_type = BranchType.items[branch_type]
        except KeyError:
            raise UnknownBranchTypeError(
                'Unknown branch type: %r' % (branch_type,))
        branches = getUtility(IBranchSet).getPullQueue(branch_type)
        return [self._getBranchPullInfo(branch) for branch in branches]

    def mirrorComplete(self, branch_id, last_revision_id):
        """See `IBranchDetailsStorage`."""
        branch = getUtility(IBranchSet).get(branch_id)
        if branch is None:
            return False
        # See comment in startMirroring.
        removeSecurityProxy(branch).mirrorComplete(last_revision_id)
        return True

    def mirrorFailed(self, branch_id, reason):
        """See `IBranchDetailsStorage`."""
        branch = getUtility(IBranchSet).get(branch_id)
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

    def startMirroring(self, branch_id):
        """See `IBranchDetailsStorage`."""
        branch = getUtility(IBranchSet).get(branch_id)
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
