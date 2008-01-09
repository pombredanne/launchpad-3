# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Base classes for HTTP resources."""

__metaclass__ = type
__all__ = [
    'HTTPResource',
    'ReadOnlyResource'
    ]

import simplejson
from zope.interface import implements
from canonical.lazr.interfaces import (IHTTPResource, IJSONPublishable)

class ResourceJSONEncoder(simplejson.JSONEncoder):

    def default(self, obj):
        if obj.implements(IJSONPublishable):
            return obj.toJSON()
        return simplejson.JSONEncoder.default(self, obj)


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
        if self.request.method == "GET":
            return self.do_GET()
        else:
            self.request.response.setStatus(405)
            self.request.response.setHeader("Allow", "GET")


class EntryResource:
    """A Launchpad object, published to the web.

    This is not a real resource yet--you can't really access it from the
    web. It's only used to compose collection resources.
    """
    implements(IEntryResource)

    def toDictionary(self):
        """Turn this object into a dictionary.

        The dictionary contains all fields defined by the resource
        interface.
        """
        dict = {}
        for name in self.resourceInterface().names(False):
            dict[name] = self.getattr(name)
        return dict

    def toJSON(self):
        """Render a JSON representation of this object."""
        return simplejson.dumps(self.toDictionary())


class CollectionResource(ReadOnlyResource):
    implements(ICollectionResource)
    """A resource that serves a list of entry resources."""

    def do_GET(self):
        """Fetch a collection and render it as JSON."""
        entry_resources = self.find():
        return ResourceJSONEncoder().encode(entry_resources)
