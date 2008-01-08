# Copyright 2008 Canonical Ltd.  All rights reserved.
"""Base classes for HTTP resources."""

__metaclass__ = type

__all__ = [
    'HTTPResource',
]

from zope.interface import implements
from canonical.lazr.interfaces import IHTTPResource

class HTTPResource:
    implements(IHTTPResource)
    """See `IHTTPResource`."""

    def __init__(self, request):
        """Store the request for later processing."""
        self.request = request

    def __call__(self):
        """See `IHTTPResource`."""
        pass
