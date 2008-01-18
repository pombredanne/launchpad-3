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
    'ServiceRoot',
    'ServiceRootResource'
    ]


import simplejson
from zope.interface import implements
from zope.publisher.interfaces import IPublishTraverse, NotFound
from zope.schema.interfaces import IField
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData
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
    implements(IHTTPResource, ICanonicalUrlData)

    def __init__(self, context, root_resource, request):
        self.context = context
        self.root_resource = root_resource
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

    @property
    def rootsite(self):
        """Find the ServiceRoot object associated with this entry.

        Use that object's rootsite.
        """
        return self.root_resource.rootsite

    @property
    def inside(self):
        """Find the top-level collection resource associated with this entry.
        """
        return self.root_resource.topLevelCollectionResource(
            self.context.parent_collection_name)

    def __init__(self, context, root_resource, request):
        """Associate this resource with a specific object and request."""
        super(EntryResource, self).__init__(IEntry(context),
                                            root_resource, request)

    @property
    def path(self):
        """Find the identifying fragment the entry uses for itself."""
        return self.context.fragment()

    def toDataForJSON(self):
        """Turn the object into a simple data structure.

        In this case, a dictionary containing all fields defined by
        the resource interface.
        """
        dict = {}
        dict['self_resource'] = canonical_url(self)
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

    def __init__(self, context, root_resource, collection_name, request):
        super(CollectionResource, self).__init__(ICollection(context),
                                                 root_resource, request)
        self.collection_name = collection_name

    @property
    def rootsite(self):
        """Find the ServiceRoot object associated with this entry.

        Use that object's rootsite.
        """
        return self.root_resource.rootsite

    @property
    def inside(self):
        """All collections are presumed to be inside the service root.
        """
        return self.root_resource

    @property
    def path(self):
        return self.collection_name

    def publishTraverse(self, request, name):
        """Fetch an entry resource by name."""
        entry = self.context.lookupEntry(name)
        if entry is None:
            raise NotFound(self, name)
        else:
            return EntryResource(entry, self.root_resource, self.request)

    def do_GET(self):
        """Fetch a collection and render it as JSON."""
        entry_resources = [EntryResource(entry, self.root_resource,
                                         self.request)
                           for entry in self.context.find()]
        self.request.response.setHeader('Content-type', 'application/json')
        return ResourceJSONEncoder().encode(entry_resources)


class ServiceRootResource(ReadOnlyResource):
    """A resource that responds to GET by describing the service."""
    implements(IPublishTraverse)

    @property
    def rootsite(self):
        return self.context.rootsite
    inside = None
    path = ''

    def topLevelCollectionResource(self, name):
        if name in self.context.top_level_collections:
            return CollectionResource(
                self.context.top_level_collections[name](), self,
                name, self.request)
        return None

    def publishTraverse(self, request, name):
        resource = self.topLevelCollectionResource(name)
        if resource is None:
            raise NotFound(self, name)
        return resource

    def do_GET(self):
        """Return a description of the resource."""
        return "This is a web service."


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


class ServiceRoot:
    """A web service."""
    implements(IPublishTraverse)

    top_level_collections = {}

    def asResource(self, request):
        return ServiceRootResource(self, None, request)

    def publishTraverse(self, request, name):
        return self.asResource(request).publishTraverse(request, name)

    def __call__(self, REQUEST=None):
        if REQUEST:
            return self.asResource(REQUEST)()
