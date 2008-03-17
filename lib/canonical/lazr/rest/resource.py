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

from zope.component import adapts
from zope.interface import implements
from zope.proxy import isProxy
from zope.schema import getFields, ValidationError
from zope.schema.interfaces import IObject
from zope.security.proxy import removeSecurityProxy

from canonical.lazr.enum import BaseItem

# XXX leonardr 2008-01-25 bug=185958:
# canonical_url code should be moved into lazr.
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData
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


class EntryResource(ReadWriteResource):
    """An individual object, published to the web."""
    implements(IEntryResource, IJSONPublishable)

    def __init__(self, context, request):
        """Associate this resource with a specific object and request."""
        super(EntryResource, self).__init__(IEntry(context), request)
        self.original_context = context

    def toDataForJSON(self):
        """Turn the object into a simple data structure.

        In this case, a dictionary containing all fields defined by
        the resource interface.
        """
        data = {}
        data['self_link'] = canonical_url(self.original_context)
        for name, field in getFields(self.context.schema).items():
            value = getattr(self.context, name)
            if ICollectionField.providedBy(field):
                # The field is a collection; include a link to the
                # collection resource.
                if value is not None:
                    key = name + '_collection_link'
                    data[key] = "%s/%s" % (data['self_link'], name)
            elif IObject.providedBy(field):
                # The field is an entry; include a link to the
                # entry resource.
                if value is not None:
                    key = name + '_link'
                    data[key] = canonical_url(value)
            else:
                # It's a data field; display it as part of the
                # representation.
                data[name] = value
        return data

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
            # We chop off the end of the string rather than use .replace()
            # because there's a chance the name of the field might already
            # have "_link" or (very unlikely) "_collection_link" in it.
            if repr_name.endswith('_collection_link'):
                name = repr_name[:-16]
            elif repr_name.endswith('_link'):
                name = repr_name[:-5]
            else:
                name = repr_name
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

        original_url = canonical_url(self.original_context)
        # Make the changes.
        for name, value in validated_changeset.items():
            setattr(self.context, name, value)

        # If the modification caused the entry's URL to change, tell
        # the client about the new URL.
        new_url = canonical_url(self.original_context)
        if new_url == original_url:
            return ''
        else:
            self.request.response.setStatus(301)
            self.request.response.setHeader('Location', new_url)


class CollectionResource(ReadOnlyResource):
    """A resource that serves a list of entry resources."""
    implements(ICollectionResource)

    def do_GET(self):
        """Fetch a collection and render it as JSON."""
        entries = ICollection(self.context).find()
        if entries is None:
            entries = []
        entry_resources = [EntryResource(entry, self.request)
                           for entry in entries]
        self.request.response.setHeader('Content-type', 'application/json')
        return simplejson.dumps(entry_resources, cls=ResourceJSONEncoder)


class ScopedCollectionResource(CollectionResource):
    """Obsolete. Provides no functionality over CollectionResource, will be
    removed."""


class ServiceRootResource:
    """A resource that responds to GET by describing the service."""
    implements(IServiceRootResource, ICanonicalUrlData)

    inside = None
    path = ''
    rootsite = None

    def __call__(self, REQUEST=None):
        """Handle a GET request."""
        if REQUEST.method == "GET":
            return "This is a web service."
        else:
            REQUEST.response.setStatus(405)
            REQUEST.response.setHeader("Allow", "GET")


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
        # Unknown at this time. Should be set by our call-site.
        self.relationship = None

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
