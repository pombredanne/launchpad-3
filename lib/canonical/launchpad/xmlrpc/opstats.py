# Copyright 2006 Canonical Ltd.  All rights reserved.

"""XML-RPC interface for extracting real time stats from the appserver."""

__metaclass__ = type
__all__ = ["OpStats", "IOpStats"]

from zope.interface import Interface, implements

from canonical.launchpad.webapp import canonical_url, LaunchpadXMLRPCView

class IOpStats(Interface):
    """Interface for OpStats"""

    def opstats():
        """Return a dictionary of a number of operational statistics.

        Keys currently are:
            requests -- # requests served by this appserver.
            xml-rpc requests -- # xml-rpc requests served.
            404s -- # 404 status responses served (Not Found)
            500s -- # 500 status responses served (Unhandled exceptions)
            503s -- # 503 status responses served (Timeouts)
            3XXs -- # 300-399 status responses served (Redirection)
            4XXs -- # 400-499 status responses served (Client Errors)
            5XXs -- # 500-599 status responses served (Server Errors)
            6XXs -- # 600-600 status responses served (Internal Errors)
        """


class OpStats(LaunchpadXMLRPCView):
    """The XML-RPC API for extracting operational statistics."""
    implements(IOpStats)

    # Statistics maintained by the publication machinery. Class global.
    stats = {
            # Global
            'requests': 0, # Requests, all protocols, all statuses

            # XML-RPC specific
            'xml-rpc requests': 0, # XML-RPC requests, all statuses
            'xml-rpc faults': 0, # XML-RPC requests returning a Fault

            # HTTP specific
            'http requests': 0,
            '404s': 0, # Not Found
            '500s': 0, # Internal Server Error (eg. unhandled exception)
            '503s': 0, # Service Unavailable (eg. Timeout)
            '1XXs': 0, # Informational (Don't think Launchpad produces these)
            '2XXs': 0, # Successful
            '3XXs': 0, # Redirection
            '4XXs': 0, # Client Errors
            '5XXs': 0, # Server Errors
            '6XXs': 0, # Internal Errors
            }

    def opstats(self):
        """See IOpStats."""
        return OpStats.stats

