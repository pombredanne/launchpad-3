# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Base classes for HTTP resources."""

__metaclass__ = type
__all__ = [
    'Collection',
    'CollectionResource',
    'Entry',
    'EntryResource',
    'HTTPResource',
    'OrderBasedScopedCollection',
    'ReadOnlyResource',
    'ScopedCollection',
    'ScopedCollectionResource',
    'ServiceRootResource'
    ]

from datetime import datetime
import simplejson
import urllib

from zope.component import getMultiAdapter
from zope.interface import implements, directlyProvides
from zope.proxy import isProxy
from zope.publisher.interfaces import NotFound
from zope.schema.interfaces import IField, IObject
from zope.security.proxy import removeSecurityProxy

# XXX leonardr 2008-01-25 bug=185958:
# canonical_url code should be moved into lazr.
from canonical.launchpad.webapp import canonical_url
from canonical.lazr.interfaces import (
    ICollection, ICollectionField, ICollectionResource, IEntry,
    IEntryResource, IHTTPResource, IJSONPublishable, IScopedCollection,
    IServiceRootResource)


class ResourceJSONEncoder(simplejson.JSONEncoder):
    """A JSON encoder for JSON-exposable resources like entry resources.

    This class works with simplejson to encode objects as JSON if they
    implement IJSONPublishable. All EntryResource subclasses, for
    instance, should implement IJSONPublishable.
    """

    def default(self, obj):
        """Convert the given object to a simple data structure."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if IJSONPublishable.providedBy(obj):
            return obj.toDataForJSON()
        if isProxy(obj):
            # We have a security-proxyied version of a built-in
            # type. We create a new version of the type by copying the
            # proxied version's content. That way the container is not
            # security proxied (and simplejson will now what do do
            # with it), but the content will still be security
            # wrapped.
            underlying_object = removeSecurityProxy(obj)
            if isinstance(underlying_object, list):
                return list(obj)
            if isinstance(underlying_object, tuple):
                return tuple(obj)
            if isinstance(underlying_object, dict):
                return dict(obj)
        return simplejson.JSONEncoder.default(self, obj) # Error out.


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
        try:
            return self.request.publication.getApplication(self.request)
        except NotFound:
            return None


class ReadOnlyResource(HTTPResource):
    """A resource that serves a string in response to GET."""

    def __call__(self):
        """Handle a GET request."""
        if self.request.method == "GET":
            return self.do_GET()
        else:
            self.request.response.setStatus(405)
            self.request.response.setHeader("Allow", "GET")


class CollectionEntryDummy:
    """An empty object providing the interface of the items in the collection.

    This is to work around the fact that getMultiAdapter() and other
    zope.component lookup methods don't accept a bare interface and only
    works with objects.
    """
    def __init__(self, collection_field):
        directlyProvides(self, collection_field.value_type.schema)


class EntryResource(ReadOnlyResource):
    """An individual object, published to the web."""
    implements(IEntryResource, IJSONPublishable)

    rootsite = None
    @property
    def inside(self):
        """See `ICanonicalUrlData`."""
        if self.parent_collection is not None:
            return self.parent_collection
        return self.root_resource.publishTraverse(
            self.request, self.context.parent_collection_name)

    def __init__(self, context, request, parent_collection = None):
        """Associate this resource with a specific object and request."""
        super(EntryResource, self).__init__(IEntry(context), request)
        self.parent_collection = parent_collection

    @property
    def path(self):
        """See `IEntryResource`."""
        path = None
        if self.parent_collection:
            # Give the parent a chance to choose its child's path.
            path = self.parent_collection.context.child_fragment(self.context)

        if path is None:
            path = urllib.quote(self.context.fragment())
        return path

    def publishTraverse(self, request, name):
        """Fetch a scoped collection resource by name."""
        field = self.context.schema.get(name)
        if not ICollectionField.providedBy(field):
            raise NotFound(self, name)
        collection = getattr(self.context, name, None)
        if collection is None:
            raise NotFound(self, name)
        # Create a dummy object that implements the field's interface.
        # This is neccessary because we can't pass the interface itself
        # into getMultiAdapter.
        example_entry = CollectionEntryDummy(field)
        scoped_collection = getMultiAdapter((self.context, example_entry),
                                             IScopedCollection)

        # Tell the IScopedCollection object what collection it's managing,
        # and what the collection's relationship is to the entry it's
        # scoped to.
        scoped_collection.collection = collection
        scoped_collection.relationship = field

        return ScopedCollectionResource(scoped_collection, self.request, name)


    def toDataForJSON(self):
        """Turn the object into a simple data structure.

        In this case, a dictionary containing all fields defined by
        the resource interface.
        """
        dict = {}
        dict['self_link'] = canonical_url(self, request=self.request)
        schema = self.context.schema
        for name in schema.names(True):
            element = schema.get(name)
            if ICollectionField.providedBy(element):
                # The field is a collection; include a link to the
                # collection resource.
                try:
                    related_resource = self.publishTraverse(
                        self.request, name)
                    key = name + '_collection_link'
                    dict[key] = canonical_url(related_resource,
                                              request=self.request)
                except NotFound:
                    pass
            elif IObject.providedBy(element):
                # The field is an entry; include a link to the
                # entry resource.
                related_entry = getattr(self.context, name)
                if related_entry is not None:
                    related_resource = EntryResource(related_entry,
                                                     self.request)
                    key = name + '_link'
                    dict[key] = canonical_url(related_resource,
                                              request=self.request)
            elif IField.providedBy(element):
                # It's a data field; display it as part of the
                # representation.
                dict[name] = getattr(self.context, name)
            else:
                # It's a method or some other part of an interface.
                # Ignore it.
                pass

        return dict

    def do_GET(self):
        """Render the entry as JSON."""
        self.request.response.setHeader('Content-type', 'application/json')
        return simplejson.dumps(self, cls=ResourceJSONEncoder)


class CollectionResource(ReadOnlyResource):
    """A resource that serves a list of entry resources."""
    implements(ICollectionResource)

    # A top-level collection resource is inside the root resource.
    inside = None
    rootsite = None

    def __init__(self, context, request, collection_name):
        """Initialize a resource for a given collection."""
        super(CollectionResource, self).__init__(
            ICollection(context), request)
        self.collection_name = collection_name

    @property
    def path(self):
        """See `ICollectionResource`."""
        return self.collection_name

    def makeEntryResource(self, entry, request):
        """Construct an entry resource for the given entry.

        This is a factory method to be overridden by subclasses.
        """
        return EntryResource(entry, request)

    def publishTraverse(self, request, name):
        """Fetch an entry resource by name."""
        entry = self.context.lookupEntry(name)
        if entry is None:
            raise NotFound(self, name)
        return self.makeEntryResource(entry, self.request)

    def do_GET(self):
        """Fetch a collection and render it as JSON."""
        entries = self.context.find()
        if entries is None:
            raise NotFound(self, self.collection_name)
        entry_resources = [self.makeEntryResource(entry, self.request)
                           for entry in entries]
        self.request.response.setHeader('Content-type', 'application/json')
        return simplejson.dumps(entry_resources, cls=ResourceJSONEncoder)


class ScopedCollectionResource(CollectionResource):
    """A resource for a collection scoped to some entry."""

    @property
    def inside(self):
        """See `ICanonicalUrlData`.

        The object to which the collection is scoped.
        """
        return EntryResource(self.context.context, self.request)

    def makeEntryResource(self, entry, request):
        """Construct an entry resource, possibly scoped to this collection.

        If this is the sort of scoped collection that contains the
        actual entries (as opposed to containing references to entries
        that 'really' live in a top-level collection), the entry resource
        will be created knowing who its parent is.
        """
        if self.context.relationship.is_entry_container:
            parent_collection = self
        else:
            parent_collection = None
        return EntryResource(entry, request, parent_collection)


class ServiceRootResource:
    """A resource that responds to GET by describing the service."""
    implements(IServiceRootResource)

    inside = None
    path = ''
    rootsite = None

    @property
    def top_level_collections(self):
        return {}

    def __call__(self, REQUEST=None):
        """Handle a GET request."""
        if REQUEST.method == "GET":
            return "This is a web service."
        else:
            REQUEST.response.setStatus(405)
            REQUEST.response.setHeader("Allow", "GET")

    def publishTraverse(self, request, name):
        if name in self.top_level_collections:
            return CollectionResource(
                self.top_level_collections[name], request, name)
        else:
            raise NotFound(self, name)


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


class ScopedCollection:
    """A collection associated with some parent object."""
    implements(ICollection)

    def __init__(self, context, collection):
        """Initialize the scoped collection.

        :param context: The object to which the collection is scoped.
        :param collection: The scoped collection.
        """
        self.context = context
        self.collection = collection

    def child_fragment(self, child):
        """Choose a URL fragment for one of this collection's entries.

        The default behavior is to let the child entry choose its own
        URL fragment. But sometimes the child doesn't have a top-level
        collection or unique ID of its own; it only makes sense in
        relation to its parent collection. In such cases it's the
        parent collection's job to decide on a URL.
        """
        return None

    def lookupEntry(self, name):
        """See `ICollection`"""
        raise KeyError(name)

    def find(self):
        """See `ICollection`."""
        return self.collection


class OrderBasedScopedCollection(ScopedCollection):
    """A scoped collection where the entries are identified by order.

    The entries in this collection don't have unique IDs of their own.
    They're identified by their ordering within this collection. So
    their URLs look like /collection/1, /collection/2, etc. The
    numbers start from 1.
    """

    def child_fragment(self, child):
        """Choose a URL fragment for one of this collection's entries.

        The default behavior is to let the child entry choose its own
        URL fragment. But sometimes the child doesn't have a top-level
        collection or unique ID of its own; it only makes sense in
        relation to its parent collection. In such cases it's the
        parent collection's job to decide on a URL.
        """
        for i, entry in enumerate(self.collection):
            if child.context == entry:
                return str(i+1)
        else:
            return None

    def lookupEntry(self, number):
        """Find a message by its order number."""
        try:
            number = int(number)
        except ValueError:
            return None
        try:
            return self.collection[number-1]
        except IndexError:
            return None
