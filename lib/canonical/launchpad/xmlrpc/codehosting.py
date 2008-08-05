# Copyright 2007 Canonical Ltd.  All rights reserved.

"""The branch details XML-RPC API."""

__metaclass__ = type
__all__ = [
    'BranchDetailsStorageAPI',
    'BranchFileSystemAPI',
    ]


from canonical.launchpad.interfaces.codehosting import (
    IBranchDetailsStorage, IBranchFileSystem)
from canonical.launchpad.webapp import LaunchpadXMLRPCView

from zope.interface import implements


class BranchDetailsStorageAPI(LaunchpadXMLRPCView):
    """See `IBranchDetailsStorage`."""

    implements(IBranchDetailsStorage)

    def getBranchPullQueue(self, branch_type):
        """See `IBranchDetailsStorage`."""
        return []


class BranchFileSystemAPI(LaunchpadXMLRPCView):
    """See `IBranchFileSystem`."""

    implements(IBranchFileSystem)

    def getBranchesForUser(self, personID):
        """See `IBranchFileSystem`."""
        return []
