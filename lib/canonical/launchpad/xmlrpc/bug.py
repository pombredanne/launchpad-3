# Copyright 2006 Canonical Ltd.  All rights reserved.

"""XML-RPC APIs for Malone."""

__metaclass__ = type
__all__ = ["FileBugAPI"]

from canonical.launchpad.webapp import LaunchpadXMLRPCView

class FileBugAPI(LaunchpadXMLRPCView):

    def report_bug(self, title):
        return title
