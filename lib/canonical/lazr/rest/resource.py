# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Base classes for HTTP resources."""

__metaclass__ = type
__all__ = [
    'Collection',
    'CollectionResource',
    'Entry',
    'EntryResource',
    'HTTPResource',
    'JSONItem',
    'OrderBasedScopedCollection',
    'ReadOnlyResource',
    'ScopedCollection',
    'ScopedCollectionResource',
    'ServiceRootResource'
    ]

from datetime import datetime
import simplejson
import urllib

from zope.component import adapts, getMultiAdapter
from zope.interface import implements, directlyProvides
from zope.proxy import isProxy
from zope.publisher.interfaces import NotFound
from zope.schema import ValidationError
from zope.schema.interfaces import IField, IObject
from zope.security.proxy import removeSecurityProxy

from canonical.lazr.enum import BaseItem

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
        if isProxy(obj):
            # We have a security-proxied version of a built-in
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
        return IJSONPublishable(obj).toDataForJSON()


class JSONItem:
    """JSONPublishable adapter for lazr.enum."""
    adapts(BaseItem)
    implements(IJSONPublishable)

    def __init__(self, context):
        self.context = context

    def toDataForJSON(self):
        """See `ISJONPublishable`"""
        return str(self.context.title)


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


class ReadWriteResource(HTTPResource):
    """A resource that responds to GET and PATCH."""
    def __call__(self):
        """Handle a GET request."""
        if self.request.method == "GET":
            return self.do_GET()
        elif self.request.method == "PATCH":
            type = self.request.headers['Content-Type']
            representation = self.request.bodyStream.getCacheStream().read()
            return self.do_PATCH(type, representation)
        else:
            self.request.response.setStatus(405)
            self.request.response.setHeader("Allow", "GET PATCH")


class CollectionEntryDummy:
    """An empty object providing the interface of the items in the collection.

    This is to work around the fact that getMultiAdapter() and other
    zope.component lookup methods don't accept a bare interface and only
    works with objects.
    """
    def __init__(self, collection_field):
        directlyProvides(self, collection_field.value_type.schema)


class EntryResource(ReadWriteResource):
    """An individual object, published to the web."""
    implements(IEntryResource, IJSONPublishable)

    rootsite = None
    @property
    def inside(self):
        """See `ICanonicalUrlData`."""
        return self.parent_collection

    def __init__(self, context, request, parent_collection = None):
        """Associate this resource with a specific object and request."""
        super(EntryResource, self).__init__(IEntry(context), request)
        if parent_collection:
            self.parent_collection = parent_collection
        else:
            resource = self.root_resource
            for fragment in self.context._parent_collection_path:
                if callable(fragment):
                    # Ask the context to do the traversal from a
                    # collection to a specific item in that
                    # collection.
                    resource = resource.makeEntryResource(
                        fragment(self.context), self.request)
                else:
                    # Traverse from an entry to one of the entry's
                    # collections, by name.
                    resource = resource.publishTraverse(self.request,
                                                        fragment)
            self.parent_collection = resource

    @property
    def path(self):
        """See `IEntryResource`."""
        path = self.parent_collection.getEntryPath(self.context)
        return urllib.quote(path)

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
            elif IField.providedBy(element) and not name.startswith('_'):
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

    def do_PATCH(self, media_type, representation):
        """Apply a JSON patch to the entry."""
        if media_type != 'application/json':
            self.request.response.setStatus(415)
            return
        changeset = simplejson.loads(unicode(representation))
        schema = self.context.schema
        validated_changeset = {}
        for repr_name, value in changeset.items():
            name = repr_name
            if repr_name.endswith('_collection_link'):
                name = repr_name[:-16]
            elif repr_name.endswith('_link'):
                name = repr_name[:-5]
            element = schema.get(name)

            if (name.startswith('_') or element is None
                or ((ICollection.providedBy(element)
                     or IObject.providedBy(element)) and repr_name == name)):
                # That last clause needs some explaining. It's the
                # situation where we have a collection represented as
                # 'foo_collection_link' or an object represented as
                # 'bar_link', and the user sent in a PATCH request
                # that tried to change 'foo' or 'bar'. This code tells
                # the user: you can't change 'foo' or 'bar' directly;
                # you have to use 'foo_collection_link' or 'bar_link'.
                # (Of course, you also can't change
                # 'foo_collection_link', but that's taken care of
                # directly below.)
                self.request.response.setStatus(400)
                return ("You tried to modify the nonexistent attribute '%s'"
                        % repr_name)

            if ICollectionField.providedBy(element):
                self.request.response.setStatus(400)
                return ("You tried to modify the collection link '%s'"
                        % repr_name)

            if element.readonly:
                self.request.response.setStatus(400)
                return ("You tried to modify the read-only attribute '%s'"
                        % repr_name)

            if IObject.providedBy(element):
                # TODO: 'value' is the URL to an object. Traverse
                # the URL to find the actual object.
                pass

            try:
                # Do any field-specific validation.
                field = element.bind(self.context)
                field.validate(value)
            except ValidationError, e:
                self.request.response.setStatus(400)
                return str(e)
            validated_changeset[name] = value

        original_url = canonical_url(self, request=self.request)
        # Make the changes.
        for name, value in validated_changeset.items():
            setattr(self.context, name, value)

        # If the modification caused the entry's URL to change, tell
        # the client about the new URL.
        new_url = canonical_url(self, request=self.request)
        if new_url == original_url:
            return ''
        else:
            self.request.response.setStatus(301)
            self.request.response.setHeader('Location', new_url)


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

    def getEntryPath(self, entry):
        """See `ICollectionResource`."""
        return self.context.getEntryPath(entry)

    def makeEntryResource(self, entry, request):
        """See `ICollectionResource`."""
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
    implements(IScopedCollection)

    def __init__(self, context, collection):
        """Initialize the scoped collection.

        :param context: The object to which the collection is scoped.
        :param collection: The scoped collection.
        """
        self.context = context
        self.collection = collection

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

    def getEntryPath(self, child):
        """See `ICollection`."""
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
