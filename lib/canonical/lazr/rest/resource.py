# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Base classes for HTTP resources."""

__metaclass__ = type
__all__ = [
    'HTTPResource',
    'ReadOnlyResource'
    ]

from zope.interface import implements
from canonical.lazr.interfaces import IHTTPResource


class HTTPResource:
    """See `IHTTPResource`."""
    implements(IHTTPResource)

    def __init__(self, request):
        """Store the request for later processing."""
        self.request = request

    def __call__(self):
        """See `IHTTPResource`."""
        pass


class ReadOnlyResource(HTTPResource):
    """A resource that serves a string in response to GET."""

    def __call__(self):
        """Handle a GET request."""
        result = self.do_GET()
        if self.request.method == "GET":
            return result
        else:
            self.request.response.setStatus(405)
            self.request.response.setHeader("Allow", "GET")
