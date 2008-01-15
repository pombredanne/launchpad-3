# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Base classes for HTTP resources."""

__metaclass__ = type
__all__ = [
    'Collection',
    'CollectionResource',
    'Entry',
    'EntryResource',
    'HTTPResource',
    'ReadOnlyResource'
    ]


import simplejson
from zope.interface import implements
from zope.publisher.interfaces import NotFound
from zope.schema.interfaces import IField
from canonical.lazr.interfaces import (
    ICollection, ICollectionResource, IEntry, IHTTPResource, IJSONPublishable)

class ResourceJSONEncoder(simplejson.JSONEncoder):
    """A JSON encoder for JSON-exposable resources like entry resources.

    This class works with simplejson to encode objects as JSON if they
    implement IJSONPublishable. All EntryResource subclasses, for
    instance, should implement IJSONPublishable.
    """

    def default(self, obj):
        """Convert the given object to a simple data structure."""
        if IJSONPublishable.providedBy(obj):
            return obj.toDataForJSON()
        return super(ResourceJSONEncoder, self).default(obj)


class HTTPResource:
    """See `IHTTPResource`."""
    implements(IHTTPResource)

    def __init__(self, context, request):
        self.context = context
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


class EntryResource(ReadOnlyResource):
    """An individual object, published to the web."""
    implements(IJSONPublishable)

    def __init__(self, context, request):
        """Associate this resource with a specific object and request."""
        self.context = IEntry(context)
        self.request = request

    def toDataForJSON(self):
        """Turn the object into a simple data structure.

        In this case, a dictionary containing all fields defined by
        the resource interface.
        """
        dict = {}
        schema = self.context.schema
        for name in schema.names():
            if IField.providedBy(schema.get(name)):
                dict[name] = getattr(self.context, name)
        return dict

    def do_GET(self):
        """Render the entry as JSON as JSON."""
        self.request.response.setHeader('Content-type', 'application/json')
        return ResourceJSONEncoder().encode(self)


class CollectionResource(ReadOnlyResource):
    """A resource that serves a list of entry resources."""
    implements(ICollectionResource)

    def __init__(self, context, request):
        self.context = ICollection(context)
        self.request = request

    def publishTraverse(self, request, name):
        """Fetch an entry resource by name."""
        entry = self.context.lookupEntry(name)
        if entry is None:
            raise NotFound(self, name)
        else:
            return EntryResource(entry, self.request)

    def do_GET(self):
        """Fetch a collection and render it as JSON."""
        entry_resources = [EntryResource(entry, self.request)
                           for entry in self.context.find()]
        self.request.response.setHeader('Content-type', 'application/json')
        return ResourceJSONEncoder().encode(entry_resources)


class Entry:
    """An individual entry."""
    implements(IEntry)

    def __init__(self, context):
        """Associate the entry with some database business object."""
        self.context = context

class Collection:
    """A collection of entries."""
    implements(ICollection)

    def __init__(self, context):
        """Associate the entry with some database business object."""
        self.context = context
