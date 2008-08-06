# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Implementations of the XML-RPC APIs for codehosting."""

__metaclass__ = type
__all__ = [
    'PullerAPI',
    'BranchFileSystem',
    ]


from canonical.launchpad.interfaces.codehosting import (
    IPullerAPI, IBranchFileSystem)
from canonical.launchpad.webapp import LaunchpadXMLRPCView

from zope.interface import implements


class PullerAPI(LaunchpadXMLRPCView):
    """See `IPullerAPI`."""

    implements(IPullerAPI)

    def getBranchPullQueue(self, branch_type):
        """See `IPullerAPI`."""
        return []


class BranchFileSystem(LaunchpadXMLRPCView):
    """See `IBranchFileSystem`."""

    implements(IBranchFileSystem)

    def getBranchesForUser(self, personID):
        """See `IBranchFileSystem`."""
        return []
