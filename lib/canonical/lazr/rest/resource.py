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
import pytz
import simplejson
from StringIO import StringIO
import urllib
import urlparse

from zope.app.datetimeutils import (DateError, DateTimeError, DateTimeParser,
                                    SyntaxError)
from zope.component import adapts, getMultiAdapter
from zope.interface import implements, directlyProvides
from zope.proxy import isProxy
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces.browser import IBrowserApplicationRequest
from zope.publisher.base import BaseRequest
from zope.schema import Datetime, ValidationError, getFields
from zope.schema.interfaces import IField, IObject
from zope.security.proxy import removeSecurityProxy

from canonical.config import config

from canonical.lazr.enum import BaseItem
from canonical.lazr.interfaces import (
    ICollection, ICollectionField, ICollectionResource, IEntry,
    IEntryResource, IHTTPResource, IJSONPublishable, IScopedCollection,
    IServiceRootResource)

# XXX leonardr 2008-01-25 bug=185958:
# canonical_url code should be moved into lazr.
from canonical.launchpad.layers import setFirstLayer
from canonical.launchpad.webapp import canonical_url


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

    def dereference_url(self, url):
        """Look up a resource in the web service by URL.

        Representations use URLs to refer to other resources in the
        web service. When processing an incoming representation it's
        often neccessary to see which object a URL refers to. This
        method calls the URL traversal code to dereference a URL into
        a published object.

        Raises a NotFoundError if the URL does not designate a
        published object.

        :param url: The URL to a resource.
        """
        (protocol, host, path, query, fragment) = urlparse.urlsplit(url)

        request_host = self.request.get('HTTP_HOST')
        if config.vhosts.use_https:
            site_protocol = 'https'
        else:
            site_protocol = 'http'

        if (host != request_host or protocol != site_protocol or
            query != '' or fragment != ''):
            raise NotFound(self, url, self.request)

        path = map(urllib.unquote, path.split('/')[1:])
        path.reverse()

        request = BaseRequest(StringIO(), {})
        setFirstLayer(request, IBrowserApplicationRequest)
        request.setTraversalStack(path)

        publication = self.request.publication
        request.setPublication(publication)
        return request.traverse(publication.getApplication(self.request))


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
    """A resource that responds to GET, PUT, and PATCH."""
    def __call__(self):
        """Handle a GET, PUT, or PATCH request."""
        if self.request.method == "GET":
            return self.do_GET()
        elif self.request.method in ["PUT", "PATCH"]:
            type = self.request.headers['Content-Type']
            representation = self.request.bodyStream.getCacheStream().read()
            if self.request.method == "PUT":
                return self.do_PUT(type, representation)
            else:
                return self.do_PATCH(type, representation)
        else:
            self.request.response.setStatus(405)
            self.request.response.setHeader("Allow", "GET PUT PATCH")


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

    def getContext(self):
        return self.context

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

    def processAsJSONHash(self, media_type, representation):
        """Process an incoming representation as a JSON hash.

        :param media_type: The specified media type of the incoming
        representation.

        :representation: The incoming representation:

        :return: A tuple (dictionary, error). 'dictionary' is a Python
        dictionary corresponding to the incoming JSON hash. 'error' is
        an error message if the incoming representation could not be
        processed. If there is an error, this method will set an
        appropriate HTTP response code.
        """

        if media_type != 'application/json':
            self.request.response.setStatus(415)
            return None, 'Expected a media type of application/json.'
        try:
            h = simplejson.loads(unicode(representation))
        except ValueError:
            self.request.response.setStatus(400)
            return None, "Entity-body was not a well-formed JSON document."
        if not isinstance(h, dict):
            self.request.response.setStatus(400)
            return None, 'Expected a JSON hash.'
        return h, None

    def do_GET(self):
        """Render the entry as JSON."""
        self.request.response.setHeader('Content-type', 'application/json')
        return simplejson.dumps(self, cls=ResourceJSONEncoder)

    def do_PUT(self, media_type, representation):
        """Modify the entry's state to match the given representation.

        A PUT is just like a PATCH, except the given representation
        must be a complete representation of the entry.
        """
        changeset, error = self.processAsJSONHash(media_type, representation)
        if error is not None:
            return error

        # Make sure the representation includes values for all
        # writable attributes.
        schema = self.context.schema
        for name, field in getFields(schema).items():
            if (name.startswith('_') or ICollectionField.providedBy(field)
                or field.readonly):
                # This attribute is not part of the web service
                # interface, is a collection link (which means it's
                # read-only), or is marked read-only. It's okay for
                # the client to omit a value for this attribute.
                continue
            if IObject.providedBy(field):
                repr_name = name + '_link'
            else:
                repr_name = name
            if (changeset.get(repr_name) is None
                and getattr(self.context, name) is not None):
                # This entry has a value for the attribute, but the
                # entity-body of the PUT request didn't make any assertion
                # about the attribute. The resource's behavior under HTTP
                # is undefined; we choose to send an error.
                self.request.response.setStatus(400)
                return ("You didn't specify a value for the attribute '%s'."
                        % repr_name)
        return self._applyChanges(changeset)

    def do_PATCH(self, media_type, representation):
        """Apply a JSON patch to the entry."""
        changeset, error = self.processAsJSONHash(media_type, representation)
        if error is not None:
            return error
        return self._applyChanges(changeset)

    def _applyChanges(self, changeset):
        """Apply a dictionary of key-value pairs as changes to an entry.

        :param changeset: A dictionary. Should come from an incoming
        representation.
        """
        validated_changeset = {}
        for repr_name, value in changeset.items():
            if repr_name == 'self_link':
                # The self link isn't part of the schema, so it's
                # handled separately.
                if value == canonical_url(self, request=self.request):
                    continue
                else:
                    self.request.response.setStatus(400)
                    return ("You tried to modify the read-only attribute "
                            "'self_link'.")

            change_this_field = True

            # We chop off the end of the string rather than use .replace()
            # because there's a chance the name of the field might already
            # have "_link" or (very unlikely) "_collection_link" in it.
            if repr_name.endswith('_collection_link'):
                name = repr_name[:-16]
            elif repr_name.endswith('_link'):
                name = repr_name[:-5]
            else:
                name = repr_name
            element = self.context.schema.get(name)

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
                # below.)
                self.request.response.setStatus(400)
                return ("You tried to modify the nonexistent attribute '%s'"
                        % repr_name)

            # Around this point the specific value provided by the client
            # becomes relevant, so we pre-process it if neccessary.
            if (IObject.providedBy(element)
                and not ICollectionField.providedBy(element)):
                # 'value' is the URL to an object. Dereference the URL
                # to find the actual object.
                try:
                    value = self.dereference_url(value).getContext()
                except NotFound:
                    self.request.response.setStatus(400)
                    return ("Your value for the attribute '%s' wasn't "
                            "the URL to any object published by this web "
                            "service." % repr_name)
                underlying_object = removeSecurityProxy(value)
                value = underlying_object.context
                # The URL points to an object, but is it an object of the
                # right type?
                if not element.schema.providedBy(value):
                    self.request.response.setStatus(400)
                    return ("Your value for the attribute '%s' doesn't "
                            "point to the right kind of object." % repr_name)
            elif isinstance(element, Datetime):
                try:
                    value = DateTimeParser().parse(value)
                    (year, month, day, hours, minutes, secondsAndMicroseconds,
                     timezone) = value
                    seconds = int(secondsAndMicroseconds)
                    microseconds = int(round((secondsAndMicroseconds - seconds)
                                             * 1000000))
                    if timezone not in ['Z', '+0000', '-0000']:
                        self.request.response.setStatus(400)
                        return ("You set the attribute '%s' to a time "
                                "that's not UTC."
                                % repr_name)
                    value = datetime(year, month, day, hours, minutes,
                                     seconds, microseconds, pytz.utc)
                except (DateError, DateTimeError, SyntaxError):
                    self.request.response.setStatus(400)
                    return ("You set the attribute '%s' to a value "
                            "that doesn't look like a date." % repr_name)

            # The current value of the attribute also becomes
            # relevant, so we obtain that. If the attribute designates
            # a collection, the 'current value' is considered to be
            # the URL to that entry or collection.
            if ICollectionField.providedBy(element):
                current_value = canonical_url(
                    self.publishTraverse(self.request, name), self.request)
            elif IObject.providedBy(element):
                current_value = EntryResource(
                    getattr(self.context, name), self.request)
            else:
                current_value = getattr(self.context, name)

            # Read-only attributes and collection links can't be
            # modified. It's okay to specify a value for an attribute
            # that can't be modified, but the new value must be the
            # same as the current value.  This makes it possible to
            # GET a document, modify one field, and send it back.
            if ICollectionField.providedBy(element):
                change_this_field = False
                if value != current_value:
                    self.request.response.setStatus(400)
                    return ("You tried to modify the collection link '%s'"
                            % repr_name)

            if element.readonly:
                change_this_field = False
                if value != current_value:
                    self.request.response.setStatus(400)
                    return ("You tried to modify the read-only attribute '%s'"
                            % repr_name)

            if change_this_field is True and value != current_value:
                if not IObject.providedBy(element):
                    try:
                        # Do any field-specific validation.
                        field = element.bind(self.context)
                        field.validate(value)
                    except ValidationError, e:
                        self.request.response.setStatus(400)
                        error = str(e)
                        if error is "":
                            error = "Validation error"
                        return error
                validated_changeset[name] = value

        # Store the entry's current URL so we can see if it changes.
        original_url = canonical_url(self, request=self.request)
        # Make the changes.
        for name, value in validated_changeset.items():
            setattr(self.context, name, value)

        # If the modification caused the entry's URL to change, tell
        # the client about the new URL.
        new_url = canonical_url(self, request=self.request)
        if new_url != original_url:
            self.request.response.setStatus(301)
            self.request.response.setHeader('Location', new_url)
        return ''


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
