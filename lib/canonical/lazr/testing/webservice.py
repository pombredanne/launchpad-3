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

from canonical.lazr.interfaces.rest import WebServiceLayer


class FakeResponse(object):
    """Simple response wrapper object."""
    def __init__(self):
        self.status = 200
        self.headers = {}

    def setStatus(self, new_status):
        self.status = new_status

    def setHeader(self, name, value):
        self.headers[name] = value


class FakeRequest(object):
    """Simple request object for testing purpose."""
    # IHTTPApplicationRequest makes us eligible for 
    # get_current_browser_request()
    implements(IHTTPApplicationRequest, WebServiceLayer)

    def __init__(self):
        self.response = FakeResponse()
        self.principal = None
        self.interaction = None

    def getApplicationURL(self):
        return "http://api.example.org"


def pprint_entry(json_body):
    """Pretty-print a webservice entry JSON representation."""
    for key, value in sorted(json_body.items()):
        print '%s: %r' % (key, value)

