# Copyright 2007 Canonical Ltd.  All rights reserved.

"""The branch details XML-RPC API."""

__metaclass__ = type
__all__ = [
    'BranchDetailsStorageAPI',
    ]


from zope.component import getUtility
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.branch import IBranchSet
from canonical.launchpad.interfaces.codehosting import (
    IBranchDetailsStorage)
from canonical.launchpad.webapp import LaunchpadXMLRPCView


# XXX:
# - removeSecurityProxy still needed?
# - branchID -> branch_id

class BranchDetailsStorageAPI(LaunchpadXMLRPCView):
    """See `IBranchDetailsStorage`."""

    implements(IBranchDetailsStorage)

    def getBranchPullQueue(self, branch_type):
        """See `IBranchDetailsStorage`."""
        return []

    def mirrorFailed(self, branchID, reason):
        """See `IBranchDetailsStorage`."""
        branch = getUtility(IBranchSet).get(branchID)
        if branch is None:
            return False
        # See comment in startMirroring.
        removeSecurityProxy(branch).mirrorFailed(reason)
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
