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
    'ReadOnlyResource',
    'ScopedCollection',
    'ServiceRootResource',
    'URLDereferencingMixin',
    ]

from datetime import datetime
import simplejson

from zope.app.pagetemplate.engine import TrustedAppPT
from zope.component import adapts, getAdapters, getMultiAdapter
from zope.component.interfaces import ComponentLookupError
from zope.interface import implements
from zope.pagetemplate.pagetemplatefile import PageTemplateFile
from zope.proxy import isProxy
from zope.publisher.interfaces import NotFound
from zope.schema import ValidationError, getFields
from zope.schema.interfaces import IObject
from zope.security.proxy import removeSecurityProxy
from zope.schema.interfaces import RequiredMissing, ValidationError
from canonical.lazr.enum import BaseItem

# XXX leonardr 2008-01-25 bug=185958:
# canonical_url and BatchNavigator code should be moved into lazr.
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData
from canonical.lazr.interfaces import (
    ICollection, ICollectionField, ICollectionResource, IEntry,
    IEntryResource, IFieldDeserializer, IHTTPResource, IJSONPublishable,
    IResourceGETOperation, IResourcePOSTOperation, IScopedCollection,
    IServiceRootResource)
from canonical.lazr.rest.schema import URLDereferencingMixin


class LazrPageTemplateFile(TrustedAppPT, PageTemplateFile):
    "A page template class for generating web service-related documents."
    pass


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


class HTTPResource(URLDereferencingMixin):
    """See `IHTTPResource`."""
    implements(IHTTPResource)

    # Some interesting media types.
    WADL_TYPE = 'application/vd.sun.wadl+xml'
    JSON_TYPE = 'application/json'

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        """See `IHTTPResource`."""
        pass

    def implementsPOST(self):
        """Returns True if this resource will respond to POST.

        Right now this means the resource has defined one or more
        custom POST operations.
        """
        adapters = getAdapters((self.context, self.request),
                               IResourcePOSTOperation)
        return len(adapters) > 0

    def getPreferredContentTypes(self):
        """Find which content types the client prefers to receive."""
        return self._parseAcceptStyleHeader(self.request.get('HTTP_ACCEPT'))

    def _parseAcceptStyleHeader(self, value):
        """Parse an HTTP header from the Accept-* family.

        These headers contain a list of possible values, each with an
        optional priority.

        This code is modified from Zope's
        BrowserLanguages#getPreferredLanguages.

        :return: All values, in descending order of priority.
        """
        if value is None:
            return []

        values = value.split(',')
        # In the original getPreferredLanguages there was some language
        # code normalization here, which I removed.
        values = [v for v in values if v != ""]

        accepts = []
        for index, value in enumerate(values):
            l = value.split(';', 2)

            # If not supplied, quality defaults to 1...
            quality = 1.0

            if len(l) == 2:
                q = l[1]
                if q.startswith('q='):
                    q = q.split('=', 2)[1]
                    quality = float(q)

            if quality == 1.0:
                # ... but we use 1.9 - 0.001 * position to
                # keep the ordering between all items with
                # 1.0 quality, which may include items with no quality
                # defined, and items with quality defined as 1.
                quality = 1.9 - (0.001 * index)

            accepts.append((quality, l[0].strip()))

        accepts = [acc for acc in accepts if acc[0] > 0]
        accepts.sort()
        accepts.reverse()
        return [value for quality, value in accepts]


class WebServiceBatchNavigator(BatchNavigator):
    """A batch navigator that speaks to web service clients.

    This batch navigator differs from others in the names of the query
    variables it expects. This class expects the starting point to be
    contained in the query variable "ws_start" and the size of the
    batch to be contained in the query variable ""ws_size". When this
    navigator serves links, it includes query variables by those
    names.
    """

    start_variable_name = "ws_start"
    batch_variable_name = "ws_size"


class BatchingResourceMixin:

    """A mixin for resources that need to batch lists of entries."""

    def batch(self, entries, request):
        """Prepare a batch from a (possibly huge) list of entries.

        :return: A hash:
        'entries' contains a list of EntryResource objects for the
          entries that actually made it into this batch
        'total_size' contains the total size of the list.
        'next_url', if present, contains a URL to get the next batch
         in the list.
        'prev_url', if present, contains a URL to get the previous batch
         in the list.
        'start' contains the starting index of this batch
        """
        navigator = WebServiceBatchNavigator(entries, request)
        resources = [EntryResource(entry, request)
                     for entry in navigator.batch]
        batch = { 'entries' : resources,
                  'total_size' : navigator.batch.listlength,
                  'start' : navigator.batch.start }
        next_url = navigator.nextBatchURL()
        if next_url != "":
            batch['next_collection_link'] = next_url
        prev_url = navigator.prevBatchURL()
        if prev_url != "":
            batch['prev_collection_link'] = prev_url
        return batch


class CustomOperationResourceMixin(BatchingResourceMixin):

    """A mixin for resources that implement a collection-entry pattern."""

    def handleCustomGET(self, operation_name):
        """Execute a custom search-type operation triggered through GET.

        This is used by both EntryResource and CollectionResource.

        :param operation_name: The name of the operation to invoke.
        :return: The result of the operation: either a string or an
        object that needs to be serialized to JSON.
        """
        operation = getMultiAdapter((self.context, self.request),
                                    IResourceGETOperation,
                                    name=operation_name)
        return self._processCustomOperationResult(operation())

    def handleCustomPOST(self, operation_name):
        """Execute a custom write-type operation triggered through POST.

        This is used by both EntryResource and CollectionResource.

        :param operation_name: The name of the operation to invoke.
        :return: The result of the operation: either a string or an
        object that needs to be serialized to JSON.
        """
        try:
            operation = getMultiAdapter((self.context, self.request),
                                        IResourcePOSTOperation,
                                        name=operation_name)
        except ComponentLookupError:
            self.request.response.setStatus(400)
            return "No such operation: " + operation_name
        return self._processCustomOperationResult(operation())

    def do_POST(self):
        """Invoke a custom operation.

        XXX leonardr 2008-04-01 bug=210265:
        The standard meaning of POST (ie. when no custom operation is
        specified) is "create a new subordinate resource."  Code
        should eventually go into CollectionResource that implements
        POST to create a new entry inside the collection.
        """
        operation_name = self.request.form.get('ws_op')
        if operation_name is None:
            self.request.response.setStatus(400)
            return "No operation name given."
        del self.request.form['ws_op']
        return self.handleCustomPOST(operation_name)

    def _processCustomOperationResult(self, result):
        """Process the result of a custom operation."""
        if isinstance(result, basestring):
            # The operation took care of everything and just needs
            # this string served to the client.
            return result

        # The operation returned a collection or entry. It will be
        # serialized to JSON.
        try:
            iterator = iter(result)
        except TypeError:
            # Result is a single entry
            return EntryResource(result, self.request)

        # Serve a single batch from the collection.
        return self.batch(result, self.request)


class ReadOnlyResource(HTTPResource):
    """A resource that serves a string in response to GET."""

    def __call__(self):
        """Handle a GET or (if implemented) POST request."""
        if self.request.method == "GET":
            return self.do_GET()
        elif self.request.method == "POST" and self.implementsPOST():
            return self.do_POST()
        else:
            if self.implementsPOST():
                allow_string = "GET POST"
            else:
                allow_string = "GET"
            self.request.response.setStatus(405)
            self.request.response.setHeader("Allow", allow_string)


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
        elif self.request.method == "POST" and self.implementsPOST():
            return self.do_POST()
        else:
            if self.implementsPOST():
                allow_string = "GET POST PUT PATCH"
            else:
                allow_string = "GET PUT PATCH"
            self.request.response.setStatus(405)
            self.request.response.setHeader("Allow", allow_string)


class EntryResource(ReadWriteResource, CustomOperationResourceMixin):
    """An individual object, published to the web."""
    implements(IEntryResource, IJSONPublishable)

    def __init__(self, context, request):
        """Associate this resource with a specific object and request."""
        super(EntryResource, self).__init__(context, request)
        self.entry = IEntry(context)

    def toDataForJSON(self):
        """Turn the object into a simple data structure.

        In this case, a dictionary containing all fields defined by
        the resource interface.
        """
        data = {}
        data['self_link'] = canonical_url(self.context)
        for name, field in getFields(self.entry.schema).items():
            value = getattr(self.entry, name)
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

        if media_type != self.JSON_TYPE:
            self.request.response.setStatus(415)
            return None, 'Expected a media type of %s.' % self.JSON_TYPE
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
        """Render an appropriate representation of the entry."""
        # Handle a custom operation, probably a search.
        operation_name = self.request.form.pop('ws_op', None)
        if operation_name is not None:
            result = self.handleCustomGET(operation_name)
            if isinstance(result, basestring):
                # The custom operation took care of everything and
                # just needs this string served to the client.
                return result
        else:
            # No custom operation was specified. Implement a standard
            # GET, which serves a JSON or WADL representation of the
            # entry.
            content_types = self.getPreferredContentTypes()
            try:
                wadl_pos = content_types.index(self.WADL_TYPE)
            except ValueError:
                wadl_pos = float("infinity")
            try:
                json_pos = content_types.index(self.JSON_TYPE)
            except ValueError:
                json_pos = float("infinity")

            # If the client's desire for WADL outranks its desire for
            # JSON, serve WADL.  Otherwise, serve JSON.
            if wadl_pos < json_pos:
                result = self.toWADL().encode("utf-8")
                self.request.response.setHeader(
                    'Content-Type', self.WADL_TYPE)
                return result
            else:
                result = self

        # Serialize the result to JSON.
        self.request.response.setHeader('Content-Type', self.JSON_TYPE)
        return simplejson.dumps(result, cls=ResourceJSONEncoder)

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
        schema = self.entry.schema
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
                and getattr(self.entry, name) is not None):
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

    def toWADL(self):
        """Represent this resource as a WADL application.

        The WADL document describes the capabilities of this resource.
        """
        template = LazrPageTemplateFile('../templates/wadl-entry.pt')
        namespace = template.pt_getContext()
        namespace['context'] = self
        return template.pt_render(namespace)

    def _applyChanges(self, changeset):
        """Apply a dictionary of key-value pairs as changes to an entry.

        :param changeset: A dictionary. Should come from an incoming
        representation.
        """
        validated_changeset = {}
        errors = []
        for repr_name, value in changeset.items():
            if repr_name == 'self_link':
                # The self link isn't part of the schema, so it's
                # handled separately.
                if value != canonical_url(self.context):
                    errors.append("self_link: "
                                  "You tried to modify a read-only attribute.")
                continue

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
            element = self.entry.schema.get(name)

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
                errors.append("%s: You tried to modify a nonexistent "
                              "attribute." % repr_name)
                continue

            # Around this point the specific value provided by the client
            # becomes relevant, so we deserialize it.
            deserializer = getMultiAdapter((element, self.request),
                                           IFieldDeserializer)
            from canonical.lazr.rest.schema import SimpleFieldDeserializer
            if repr_name == 'teamowner_link':
                import pdb; pdb.set_trace()
            try:
                value = deserializer.deserialize(value)
            except (ValueError, ValidationError), e:
                errors.append("%s: %s" % (repr_name, e))
                continue

            if (IObject.providedBy(element)
                and not ICollectionField.providedBy(element)):
                # The URL points to an object, but is it an object of the
                # right type?

                # TODO leonardr 2008-15-04
                # blueprint=api-wadl-description: This should be moved
                # into the ObjectLookupFieldDeserializer, once we make
                # it possible for Vocabulary fields to specify a
                # schema class the way IObject fields can.
                if not self.field.schema.providedBy(value):
                    errors.append("%s: Your value points to the "
                                  "wrong kind of object" % repr_name)
                    continue

            # The current value of the attribute also becomes
            # relevant, so we obtain that. If the attribute designates
            # a collection, the 'current value' is considered to be
            # the URL to that entry or collection.
            if ICollectionField.providedBy(element):
                current_value = "%s/%s" % (
                    canonical_url(self.context), name)
            elif IObject.providedBy(element):
                current_value = canonical_url(getattr(self.entry, name))
            else:
                current_value = getattr(self.entry, name)

            # Read-only attributes and collection links can't be
            # modified. It's okay to specify a value for an attribute
            # that can't be modified, but the new value must be the
            # same as the current value.  This makes it possible to
            # GET a document, modify one field, and send it back.
            if ICollectionField.providedBy(element):
                change_this_field = False
                if value != current_value:
                    errors.append("%s: You tried to modify a collection "
                                  "attribute." % repr_name)
                    continue

            if element.readonly:
                change_this_field = False
                if value != current_value:
                    errors.append("%s: You tried to modify a read-only "
                                  "attribute." % repr_name)
                    continue

            if change_this_field is True and value != current_value:
                if not IObject.providedBy(element):
                    try:
                        # Do any field-specific validation.
                        field = element.bind(self.context)
                        field.validate(value)
                    except (ValueError, ValidationError), e:
                        error = str(e)
                        if error == "":
                            error = "Validation error"
                        errors.append("%s: %s" % (name, e))
                        continue
                validated_changeset[name] = value

        # If there were errors, display them and send a status of 400.
        if len(errors) > 0:
            self.request.response.setStatus(400)
            self.request.response.setHeader('Content-type', 'text/plain')
            return "\n".join(errors)

        # Store the entry's current URL so we can see if it changes.
        original_url = canonical_url(self.context)
        # Make the changes.
        for name, value in validated_changeset.items():
            setattr(self.entry, name, value)

        # If the modification caused the entry's URL to change, tell
        # the client about the new URL.
        new_url = canonical_url(self.context)
        if new_url != original_url:
            self.request.response.setStatus(301)
            self.request.response.setHeader('Location', new_url)
        return ''


class CollectionResource(ReadOnlyResource, CustomOperationResourceMixin):
    """A resource that serves a list of entry resources."""
    implements(ICollectionResource)

    def __init__(self, context, request):
        """Associate this resource with a specific object and request."""
        super(CollectionResource, self).__init__(context, request)
        self.collection = ICollection(context)

    def do_GET(self):
        """Fetch a collection and render it as JSON."""
        # Handle a custom operation, probably a search.
        operation_name = self.request.form.pop('ws_op', None)
        if operation_name is not None:
            result = self.handleCustomGET(operation_name)
            if isinstance(result, str) or isinstance(result, unicode):
                # The custom operation took care of everything and
                # just needs this string served to the client.
                return result
        else:
            # No custom operation was specified. Implement a standard GET,
            # which retrieves the items in the collection.
            entries = self.collection.find()
            if entries is None:
                raise NotFound(self, self.collection_name)
            result = self.batch(entries, self.request)

        self.request.response.setHeader('Content-type', self.JSON_TYPE)
        return simplejson.dumps(result, cls=ResourceJSONEncoder)


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

    def find(self):
        """See `ICollection`."""
        return self.collection

