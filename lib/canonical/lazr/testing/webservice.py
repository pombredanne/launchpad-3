# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Testing helpers for webservice unit tests."""

__metaclass__ = type
__all__ = [
    'FakeRequest',
    'FakeResponse',
    'pprint_entry',
    ]

from zope.interface import implements
from zope.publisher.interfaces.http import IHTTPApplicationRequest

# XXX: JonathanLange 2008-12-18: Are we allowed to import launchpad into lazr?
from canonical.launchpad.webapp.servers import StepsToGo
from canonical.lazr.interfaces.rest import WebServiceLayer


class FakeResponse:
    """Simple response wrapper object."""
    def __init__(self):
        self.status = 599
        self.headers = {}

    def setStatus(self, new_status):
        self.status = new_status

    def setHeader(self, name, value):
        self.headers[name] = value

    def getHeader(self, name):
        """Return the value of the named header."""
        return self.headers.get(name)

    def getStatus(self):
        """Return the response status code."""
        return self.status


class FakeRequest:
    """Simple request object for testing purpose."""
    # IHTTPApplicationRequest makes us eligible for
    # get_current_browser_request()
    implements(IHTTPApplicationRequest, WebServiceLayer)

    def __init__(self, traversed=None, stack=None):
        self._traversed_names = traversed
        self._stack = stack
        self.response = FakeResponse()
        self.principal = None
        self.interaction = None
        self.traversed_objects = []

    def getTraversalStack(self):
        return self._stack

    def setTraversalStack(self, stack):
        self._stack = stack

    @property
    def stepstogo(self):
        return StepsToGo(self)

    def getApplicationURL(self):
        return "http://api.example.org"

    def get(self, key, default=None):
        """Simulate an empty set of request parameters."""
        return default


def pprint_entry(json_body):
    """Pretty-print a webservice entry JSON representation.

    Omits the http_etag key, which is always present and never
    interesting for a test.
    """
    for key, value in sorted(json_body.items()):
        if key != 'http_etag':
            print '%s: %r' % (key, value)


def pprint_collection(json_body):
    """Pretty-print a webservice collection JSON representation."""
    for key, value in sorted(json_body.items()):
        if key != 'entries':
            print '%s: %r' % (key, value)
    print '---'
    for entry in json_body['entries']:
        pprint_entry(entry)
        print '---'
