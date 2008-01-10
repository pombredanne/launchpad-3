# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Base classes for HTTP resources."""

__metaclass__ = type
__all__ = [
    'CollectionResource',
    'EntryResource',
    'HTTPResource',
    'ReadOnlyResource'
    ]


import simplejson
from zope.interface import implements
from zope.publisher.interfaces import NotFound
from canonical.lazr.interfaces import (
    ICollectionResource, IEntryResource, IHTTPResource, IJSONPublishable)

class ResourceJSONEncoder(simplejson.JSONEncoder):

    def default(self, obj):
        if IJSONPublishable.providedBy(obj):
            return obj.toJSONReady()
        return super(ResourceJSONEncoder, self).default(self, obj)


class HTTPResource:
    """See `IHTTPResource`."""
    implements(IHTTPResource)

    def __call__(self, REQUEST=None):
        """See `IHTTPResource`."""
        pass


class ReadOnlyResource(HTTPResource):
    """A resource that serves a string in response to GET."""

    def __call__(self, REQUEST=None):
        """Handle a GET request."""
        if REQUEST.method == "GET":
            return self.do_GET(REQUEST)
        else:
            REQUEST.response.setStatus(405)
            REQUEST.response.setHeader("Allow", "GET")


class EntryResource(ReadOnlyResource):
    """A Launchpad object, published to the web."""
    implements(IEntryResource)

    def toDictionary(self):
        """Turn this object into a dictionary.

        The dictionary contains all fields defined by the resource
        interface.
        """
        dict = {}
        for name in self.resourceInterface().names(False):
            dict[name] = getattr(self, name)
        return dict

    def toJSONReady(self):
        """Turn the object into a simple data structure."""
        return self.toDictionary()

    def do_GET(self, request):
        """Render an entry as JSON."""
        request.response.setHeader('Content-type', 'application/json')
        return ResourceJSONEncoder().encode(self)


class CollectionResource(ReadOnlyResource):
    implements(ICollectionResource)
    """A resource that serves a list of entry resources."""

    def publishTraverse(self, request, name):
        """Fetch an entry resource by name."""
        import pdb; pdb.set_trace()
        entry = self.lookupEntry(request, name)
        if entry is None:
            raise NotFound(self, name)
        else:
            return entry

    def do_GET(self, request):
        """Fetch a collection and render it as JSON."""
        entry_resources = self.find()
        request.response.setHeader('Content-type', 'application/json')
        return ResourceJSONEncoder().encode(entry_resources)
