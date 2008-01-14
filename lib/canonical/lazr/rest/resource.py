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
from zope.component import getAdapter
from zope.interface import implements
from canonical.lazr.interfaces import (
    ICollection, ICollectionResource, IEntry, IHTTPResource, IJSONPublishable)


class ResourceJSONEncoder(simplejson.JSONEncoder):

    def default(self, obj):
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


class EntryResource:
    """An individual object, published to the web.

    This is not a real resource yet--you can't really access it from the
    web. It's only used to compose collection resources.
    """
    implements(IJSONPublishable)

    def __init__(self, context):
        """Associate this resource with a specific object."""
        self.context = context

    def toDataForJSON(self):
        """Turn the object into a simple data structure.

        In this case, a dictionary containing all fields defined by
        the resource interface.
        """
        dict = {}
        entry_resource = getAdapter(self.context, IEntry)
        for name in entry_resource.schema.names():
            dict[name] = getattr(entry_resource, name)
        return dict


class CollectionResource(ReadOnlyResource):
    implements(ICollectionResource)
    """A resource that serves a list of entry resources."""

    def do_GET(self):
        """Fetch a collection and render it as JSON."""
        entry_resources = self.context.find()
        self.request.response.setHeader('Content-type', 'application/json')
        return ResourceJSONEncoder().encode(entry_resources)
