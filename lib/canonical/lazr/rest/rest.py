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

    def __init__(self, request):
        self.request = request

    def __call__(self):
        pass
