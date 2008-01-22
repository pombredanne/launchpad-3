# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Base classes for HTTP resources."""

__metaclass__ = type
__all__ = [
    'Collection',
    'CollectionResource',
    'Entry',
    'EntryResource',
    'HTTPResource',
    'ReadOnlyResource',
    'ServiceRootResource'
    ]


import simplejson

from zope.interface import implements
from zope.publisher.interfaces import NotFound
from zope.schema.interfaces import IField

from canonical.launchpad.webapp import canonical_url
from canonical.lazr.interfaces import (
    ICollection, ICollectionResource, IEntry, IEntryResource, IHTTPResource,
    IJSONPublishable, IServiceRootResource)


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
        return simplejson.JSONEncoder.default(self, obj)


class HTTPResource:
    """See `IHTTPResource`."""
    implements(IHTTPResource)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        """See `IHTTPResource`."""
        pass

    @property
    def root_resource(self):
        return self.request.publication.getApplication(self.request)


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
    implements(IEntryResource, IJSONPublishable)

    rootsite = None
    @property
    def inside(self):
        """Find the top-level collection resource associated with this entry.
        """
        return self.root_resource.getTopLevelCollectionResource(
            self.request, self.context.parent_collection_name)

    def __init__(self, context, request):
        """Associate this resource with a specific object and request."""
        super(EntryResource, self).__init__(IEntry(context), request)

    @property
    def path(self):
        """See `IEntryResource`."""
        return self.context.fragment()

    def toDataForJSON(self):
        """Turn the object into a simple data structure.

        In this case, a dictionary containing all fields defined by
        the resource interface.
        """
        dict = {}
        dict['self_resource'] = canonical_url(self, request=self.request)
        schema = self.context.schema
        for name in schema.names():
            if IField.providedBy(schema.get(name)):
                dict[name] = getattr(self.context, name)
        return dict

    def do_GET(self):
        """Render the entry as JSON."""
        self.request.response.setHeader('Content-type', 'application/json')
        return ResourceJSONEncoder().encode(self)


class CollectionResource(ReadOnlyResource):
    """A resource that serves a list of entry resources."""
    implements(ICollectionResource)

    def __init__(self, context, collection_name, request):
        super(CollectionResource, self).__init__(
            ICollection(context), request)
        self.collection_name = collection_name

    rootsite = None
    inside = None

    @property
    def path(self):
        """See `ICollectionResource`."""
        return self.collection_name

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


class ServiceRootResource(HTTPResource):
    """A resource that responds to GET by describing the service."""
    implements(IServiceRootResource)

    inside = None
    path = ''
    top_level_collections = {}

    def __init__(self):
        """Initialize the service root.

        Unlike other resources, which are initialized per request, the
        service root resource is initialized only once. Thus there is
        no request object. There is also no context object, because the
        service root resource just is the service root object itself.
        """
        super(ServiceRootResource, self).__init__(None, None)

    def __call__(self, REQUEST=None):
        """Handle a GET request."""
        if REQUEST.method == "GET":
            return "This is a web service."
        else:
            REQUEST.response.setStatus(405)
            REQUEST.response.setHeader("Allow", "GET")

    def getTopLevelCollectionResource(self, request, name):
        if name in self.top_level_collections:
            return CollectionResource(
                self.top_level_collections[name](), name, request)
        else:
            return None

    def publishTraverse(self, request, name):
        resource = self.getTopLevelCollectionResource(request, name)
        if resource is None:
            raise NotFound(self, name)
        else:
            return resource


class Entry:
    """An individual entry."""
    implements(IEntry)

    def __init__(self, context):
        """Associate the entry with some database model object."""
        self.context = context


class Collection:
    """A collection of entries."""
    implements(ICollection)

    def __init__(self, context):
        """Associate the entry with some database model object."""
        self.context = context
