# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Implementations of the XML-RPC APIs for codehosting."""

__metaclass__ = type
__all__ = [
    'BranchFileSystem',
    'BranchPuller',
    ]


from canonical.launchpad.interfaces.codehosting import (
    IBranchFileSystem, IBranchPuller)
from canonical.launchpad.webapp import LaunchpadXMLRPCView

from zope.interface import implements


class BranchPuller(LaunchpadXMLRPCView):
    """See `IBranchPuller`."""

    implements(IBranchPuller)

    def getBranchPullQueue(self, branch_type):
        """See `IBranchPuller`."""
        return []


class BranchFileSystem(LaunchpadXMLRPCView):
    """See `IBranchFileSystem`."""

    implements(IBranchFileSystem)

    def getBranchesForUser(self, personID):
        """See `IBranchFileSystem`."""
        return []
