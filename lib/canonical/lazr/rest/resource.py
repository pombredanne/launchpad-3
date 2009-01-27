# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Base classes for HTTP resources."""

__metaclass__ = type

__all__ = [
    'BatchingResourceMixin',
    'Collection',
    'CollectionResource',
    'Entry',
    'EntryAdapterUtility',
    'EntryResource',
    'HTTPResource',
    'JSONItem',
    'ReadOnlyResource',
    'ResourceJSONEncoder',
    'RESTUtilityBase',
    'ScopedCollection',
    'ServiceRootResource',
    'WADL_SCHEMA_FILE',
    ]


import copy
from cStringIO import StringIO
from datetime import datetime
from gzip import GzipFile
import os
import sha
import simplejson
import zlib

from zope.app import zapi
from zope.app.pagetemplate.engine import TrustedAppPT
from zope.component import (
    adapts, getAdapters, getAllUtilitiesRegisteredFor, getMultiAdapter,
    getUtility, queryAdapter)
from zope.component.interfaces import ComponentLookupError
from zope.event import notify
from zope.interface import implements, implementedBy, providedBy
from zope.interface.interfaces import IInterface
from zope.pagetemplate.pagetemplatefile import PageTemplateFile
from zope.proxy import isProxy
from zope.publisher.interfaces import NotFound
from zope.schema import ValidationError, getFieldsInOrder
from zope.schema.interfaces import (
    ConstraintNotSatisfied, IBytes, IChoice, IObject)
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy
from canonical.lazr.enum import BaseItem

# XXX leonardr 2008-01-25 bug=185958:
# canonical_url, BatchNavigator, and event code should be moved into lazr.
from canonical.launchpad import versioninfo
from canonical.launchpad.event import SQLObjectModifiedEvent
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.interfaces import (
    ICanonicalUrlData, ILaunchBag)
from canonical.launchpad.webapp.publisher import get_current_browser_request
from canonical.launchpad.webapp.snapshot import Snapshot
from canonical.lazr.interfaces import (
    ICollection, ICollectionResource, IEntry, IEntryResource,
    IFieldMarshaller, IHTTPResource, IJSONPublishable, IResourceGETOperation,
    IResourcePOSTOperation, IScopedCollection, IServiceRootResource,
    ITopLevelEntryLink, IUnmarshallingDoesntNeedValue, LAZR_WEBSERVICE_NAME)
from canonical.lazr.interfaces.fields import ICollectionField
from canonical.launchpad.webapp.vocabulary import SQLObjectVocabularyBase

# The path to the WADL XML Schema definition.
WADL_SCHEMA_FILE = os.path.join(os.path.dirname(__file__),
                                'wadl20061109.xsd')


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
            # security proxied (and simplejson will know what do do
            # with it), but the content will still be security
            # wrapped.
            underlying_object = removeSecurityProxy(obj)
            if isinstance(underlying_object, list):
                return list(obj)
            if isinstance(underlying_object, tuple):
                return tuple(obj)
            if isinstance(underlying_object, dict):
                return dict(obj)
        if queryAdapter(obj, IEntry):
            obj = EntryResource(obj, get_current_browser_request())

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

    # Some interesting media types.
    WADL_TYPE = 'application/vd.sun.wadl+xml'
    JSON_TYPE = 'application/json'

    # The representation value used when the client doesn't have
    # authorization to see the real value.
    REDACTED_VALUE = 'tag:launchpad.net:2008:redacted'

    HTTP_METHOD_OVERRIDE_ERROR = ("X-HTTP-Method-Override can only be used "
                                  "with a POST request.")

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        """See `IHTTPResource`."""
        pass

    def getRequestMethod(self, request=None):
        """Return the HTTP method of the provided (or current) request.

        This is usually the actual HTTP method, but it might be
        overridden by a value for X-HTTP-Method-Override.

        :return: None if the valid for X-HTTP-Method-Override is invalid.
        Otherwise, the HTTP method to use.
        """
        if request == None:
            request = self.request
        override = request.headers.get('X-HTTP-Method-Override')
        if override is not None:
            if request.method == 'POST':
                return override
            else:
                # XHMO should not be used unless the underlying method
                # is POST.
                self.request.response.setStatus(400)
                return None
        return request.method

    def handleConditionalGET(self):
        """Handle a possible conditional GET request.

        This method has side effects. If the resource provides a
        generated ETag, it sets this value as the "ETag" response
        header. If the "ETag" request header matches the generated
        ETag, it sets the response code to 304 ("Not Modified").

        :return: The media type to serve. If this value is None, the
            incoming ETag matched the generated ETag and there is no
            need to serve anything else.
        """
        incoming_etags = self._parseETags('If-None-Match')

        if self.getPreferredSupportedContentType() == self.WADL_TYPE:
            media_type = self.WADL_TYPE
        else:
            media_type = self.JSON_TYPE
        existing_etag = self.getETag(media_type)
        if existing_etag is not None:
            self.request.response.setHeader('ETag', existing_etag)
            if existing_etag in incoming_etags:
                # The client already has this representation.
                # No need to send it again.
                self.request.response.setStatus(304) # Not Modified
                media_type = None
        return media_type

    def handleConditionalWrite(self):
        """Handle a possible conditional PUT or PATCH request.

        This method has side effects. If the write operation should
        not continue, because the incoming ETag doesn't match the
        generated ETag, it sets the response code to 412
        ("Precondition Failed").

        If the PUT or PATCH request is being tunneled through POST
        with X-HTTP-Method-Override, the media type of the incoming
        representation will be obtained from X-Content-Type-Override
        instead of Content-Type, should X-C-T-O be provided.

        :return: The media type of the incoming representation. If
            this value is None, the incoming ETag didn't match the
            generated ETag and the incoming representation should be
            ignored.
        """
        media_type = self.request.headers.get('X-Content-Type-Override')
        if media_type is not None:
            if self.request.method != 'POST':
                # X-C-T-O should not be used unless the underlying
                # method is POST. Set response code 400 ("Bad
                # Request").
                self.request.response.setStatus(400)
                return None
        else:
            media_type = self.request.headers.get(
                'Content-Type', self.JSON_TYPE)

        incoming_etags = self._parseETags('If-Match')
        if len(incoming_etags) == 0:
            # This is not a conditional write.
            return media_type
        existing_etag = self.getETag(media_type)
        if existing_etag in incoming_etags:
            # The conditional write can continue.
            return media_type
        # The resource has changed since the client requested it.
        # Don't let the write go through. Set response code 412
        # ("Precondition Failed")
        self.request.response.setStatus(412)
        return None

    def getETag(self, media_type):
        """Calculate an ETag for a representation of this resource.

        The WADL representation of a resource only changes when the
        software itself changes. Thus, we can use the Launchpad
        revision number itself as an ETag. We delegate to subclasses
        when it comes to calculating ETags for other representations.
        """
        if media_type == self.WADL_TYPE:
            return '"%s"' % versioninfo.revno
        return None

    def applyTransferEncoding(self, representation):
        """Apply a requested transfer-encoding to the representation.

        'gzip' and 'deflate' are the only supported transfer-encodings.

        This method has side effects. If an encoding was applied, it
        sets the "Transfer-Encoding" response header to the name of
        that encoding.
        """
        if representation == "":
            # Don't compress an empty representation--that makes it nonempty.
            return ""
        requested_encodings = self._parseAcceptStyleHeader(
            self.request.get('HTTP_TE'))
        infinity = float("infinity")

        try:
            gzip_pos = requested_encodings.index('gzip')
        except ValueError:
            gzip_pos = infinity
        try:
            deflate_pos = requested_encodings.index('deflate')
        except ValueError:
            deflate_pos = infinity

        if gzip_pos < deflate_pos:
            self.request.response.setHeader("Transfer-Encoding", "gzip")
            gzipped = StringIO()
            file = GzipFile(mode="w", fileobj=gzipped)
            file.write(representation)
            file.close()
            return gzipped.getvalue()
        elif deflate_pos != infinity:
            self.request.response.setHeader("Transfer-Encoding", "deflate")
            return zlib.compress(representation)
        return representation


    def implementsPOST(self):
        """Returns True if this resource will respond to POST.

        Right now this means the resource has defined one or more
        custom POST operations.
        """
        adapters = list(
            getAdapters((self.context, self.request), IResourcePOSTOperation))
        return len(adapters) > 0

    def toWADL(self, template_name="wadl-resource.pt"):
        """Represent this resource as a WADL application.

        The WADL document describes the capabilities of this resource.
        """
        template = LazrPageTemplateFile('../templates/' + template_name)
        namespace = template.pt_getContext()
        namespace['context'] = self
        return template.pt_render(namespace)

    def getPreferredSupportedContentType(self):
        """Of the content types we serve, which would the client prefer?

        The web service supports WADL and JSON representations. The
        default is JSON. This method determines whether the client
        would rather have WADL or JSON.
        """
        content_types = self.getPreferredContentTypes()
        try:
            wadl_pos = content_types.index(self.WADL_TYPE)
        except ValueError:
            wadl_pos = float("infinity")
        try:
            json_pos = content_types.index(self.JSON_TYPE)
        except ValueError:
            json_pos = float("infinity")
        if wadl_pos < json_pos:
            return self.WADL_TYPE
        return self.JSON_TYPE

    def getPreferredContentTypes(self):
        """Find which content types the client prefers to receive."""
        return self._parseAcceptStyleHeader(self.request.get('HTTP_ACCEPT'))

    def _parseETags(self, header_name):
        """Extract a list of ETags from a header and parse the list.

        RFC2616 allows multiple comma-separated ETags.
        """
        header = self.request.getHeader(header_name)
        if header is None:
            return []
        # We're kind of cheating, because entity tags can technically
        # have commas in them, but none of our tags contain commas, so
        # this will work.
        return [etag.strip() for etag in header.split(',')]

    def _fieldValueIsObject(self, field):
        """Does the given field expect a data model object as its value?

        Obviously an IObject field is expected to have a data model
        object as its value. But an IChoice field might also have a
        vocabulary drawn from the set of data model objects.
        """
        if IObject.providedBy(field):
            return True
        if IChoice.providedBy(field):
            # Find out whether the field's vocabulary is made of
            # database objects (which correspond to resources that
            # need to be linked to) or regular objects (which can
            # be serialized to JSON).
            field = field.bind(self.context)
            return isinstance(field.vocabulary, SQLObjectVocabularyBase)
        return False

    def _parseContentDispositionHeader(self, value):
        """Parse a Content-Disposition header.

        :return: a 2-tuple (disposition-type, disposition-params).
        disposition-params is a dict mapping parameter names to values.
        """
        disposition = None
        params = {}
        if value is None:
            return (disposition, params)
        pieces = value.split(';')
        if len(pieces) > 1:
            disposition = pieces[0].strip()
        for name_value in pieces[1:]:
            name_and_value = name_value.split('=', 2)
            if len(name_and_value) == 2:
                name = name_and_value[0].strip()
                value = name_and_value[1].strip()
                # Strip quotation marks if present. RFC2183 gives
                # guidelines for when to quote these values, but it's
                # very likely that a client will quote even short
                # filenames, and unlikely that a filename will
                # actually begin and end with quotes.
                if (value[0] == '"' and value[-1] == '"'):
                    value = value[1:-1]
            else:
                name = name_and_value
                value = None
            params[name] = value
        return (disposition, params)

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
    contained in the query variable "ws.start" and the size of the
    batch to be contained in the query variable "ws.size". When this
    navigator serves links, it includes query variables by those
    names.
    """

    start_variable_name = "ws.start"
    batch_variable_name = "ws.size"


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
                     for entry in navigator.batch
                     if check_permission('launchpad.View', entry)]
        batch = { 'entries' : resources,
                  'total_size' : navigator.batch.listlength,
                  'start' : navigator.batch.start }
        if navigator.batch.start < 0:
            batch['start'] = None
        next_url = navigator.nextBatchURL()
        if next_url != "":
            batch['next_collection_link'] = next_url
        prev_url = navigator.prevBatchURL()
        if prev_url != "":
            batch['prev_collection_link'] = prev_url
        return batch


class CustomOperationResourceMixin:

    """A mixin for resources that implement a collection-entry pattern."""

    def handleCustomGET(self, operation_name):
        """Execute a custom search-type operation triggered through GET.

        This is used by both EntryResource and CollectionResource.

        :param operation_name: The name of the operation to invoke.
        :return: The result of the operation: either a string or an
        object that needs to be serialized to JSON.
        """
        try:
            operation = getMultiAdapter((self.context, self.request),
                                        IResourceGETOperation,
                                        name=operation_name)
        except ComponentLookupError:
            self.request.response.setStatus(400)
            return "No such operation: " + operation_name
        return operation()

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
        return operation()

    def do_POST(self):
        """Invoke a custom operation.

        XXX leonardr 2008-04-01 bug=210265:
        The standard meaning of POST (ie. when no custom operation is
        specified) is "create a new subordinate resource."  Code
        should eventually go into CollectionResource that implements
        POST to create a new entry inside the collection.
        """
        operation_name = self.request.form.get('ws.op')
        if operation_name is None:
            self.request.response.setStatus(400)
            return "No operation name given."
        del self.request.form['ws.op']
        return self.handleCustomPOST(operation_name)


class ReadOnlyResource(HTTPResource):
    """A resource that serves a string in response to GET."""

    def __call__(self):
        """Handle a GET or (if implemented) POST request."""
        result = ""
        method = self.getRequestMethod()
        if method is None:
            result = self.HTTP_METHOD_OVERRIDE_ERROR
        elif method == "GET":
            result = self.do_GET()
        elif method == "POST" and self.implementsPOST():
            result = self.do_POST()
        else:
            if self.implementsPOST():
                allow_string = "GET POST"
            else:
                allow_string = "GET"
            self.request.response.setStatus(405)
            self.request.response.setHeader("Allow", allow_string)
        return self.applyTransferEncoding(result)

class ReadWriteResource(HTTPResource):
    """A resource that responds to GET, PUT, and PATCH."""

    def __call__(self):
        """Handle a GET, PUT, or PATCH request."""
        result = ""
        method = self.getRequestMethod()
        if method is None:
            result = self.HTTP_METHOD_OVERRIDE_ERROR
        elif method == "GET":
            result = self.do_GET()
        elif method in ["PUT", "PATCH"]:
            media_type = self.handleConditionalWrite()
            if media_type is not None:
                stream = self.request.bodyStream
                representation = stream.getCacheStream().read()
                if method == "PUT":
                    result = self.do_PUT(media_type, representation)
                else:
                    result = self.do_PATCH(media_type, representation)
        elif method == "POST" and self.implementsPOST():
            result = self.do_POST()
        else:
            if self.implementsPOST():
                allow_string = "GET POST PUT PATCH"
            else:
                allow_string = "GET PUT PATCH"
            self.request.response.setStatus(405)
            self.request.response.setHeader("Allow", allow_string)
        return self.applyTransferEncoding(result)


class EntryResource(ReadWriteResource, CustomOperationResourceMixin):
    """An individual object, published to the web."""
    implements(IEntryResource, IJSONPublishable)

    missing = object()

    def __init__(self, context, request):
        """Associate this resource with a specific object and request."""
        super(EntryResource, self).__init__(context, request)
        self.etags_by_media_type = {}
        self.entry = IEntry(context)
        self._unmarshalled_field_cache = {}

    def getETag(self, media_type, unmarshalled_field_values=None):
        """Calculate the ETag for an entry.

        :arg unmarshalled_field_values: A dict mapping field names to
        unmarshalled values, obtained during some other operation such
        as the construction of a representation.
        """
        # Try to find a cached value.
        etag = self.etags_by_media_type.get(media_type)
        if etag is not None:
            return etag

        # Try to make the superclass handle it.
        etag = super(EntryResource, self).getETag(media_type)
        if etag is not None:
            self.etags_by_media_type[media_type] = etag
            return etag

        # Calculate the ETag for a JSON representation only.
        if media_type != self.JSON_TYPE:
            return None

        hash_object = sha.new()
        values = []
        for name, field in getFieldsInOrder(self.entry.schema):
            if self.isModifiableField(field, False):
                if (unmarshalled_field_values is not None
                    and unmarshalled_field_values.get(name)):
                    value = unmarshalled_field_values[name]
                else:
                    ignored, value = self._unmarshallField(name, field)
                values.append(unicode(value))
        hash_object.update("\0".join(values).encode("utf-8"))

        # Append the revision number, because the algorithm for
        # generating the representation might itself change across
        # versions.
        hash_object.update("\0" + str(versioninfo.revno))

        etag = '"%s"' % hash_object.hexdigest()
        self.etags_by_media_type[media_type] = etag
        return etag

    def toDataForJSON(self):
        """Turn the object into a simple data structure.

        In this case, a dictionary containing all fields defined by
        the resource interface.
        """
        data = {}
        data['self_link'] = canonical_url(self.context, self.request)
        data['resource_type_link'] = self.type_url
        unmarshalled_field_values = {}
        for name, field in getFieldsInOrder(self.entry.schema):
            repr_name, repr_value = self._unmarshallField(name, field)
            data[repr_name] = repr_value
            unmarshalled_field_values[name] =  repr_value

        etag = self.getETag(self.JSON_TYPE, unmarshalled_field_values)
        data['http_etag'] = etag
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

        if not media_type.startswith(self.JSON_TYPE):
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
        operation_name = self.request.form.pop('ws.op', None)
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
            media_type = self.handleConditionalGET()
            if media_type is None:
                # The conditional GET succeeded. Serve nothing.
                return ""
            elif media_type == self.WADL_TYPE:
                result = self.toWADL().encode("utf-8")
            elif media_type == self.JSON_TYPE:
                result = simplejson.dumps(self, cls=ResourceJSONEncoder)

        self.request.response.setHeader('Content-Type', media_type)
        return result

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
        # Get the fields ordered by name so that we always evaluate them in
        # the same order. This is needed to predict errors when testing.
        for name, field in getFieldsInOrder(self.entry.schema):
            if not self.isModifiableField(field, True):
                continue
            field = field.bind(self.context)
            marshaller = getMultiAdapter((field, self.request),
                                         IFieldMarshaller)
            repr_name = marshaller.representation_name
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

    @property
    def type_url(self):
        "The URL to the resource type for this resource."
        adapter = EntryAdapterUtility(self.entry.__class__)

        return "%s#%s" % (
            canonical_url(self.request.publication.getApplication(
                    self.request), self.request),
            adapter.singular_type)

    def isModifiableField(self, field, is_external_client):
        """Returns true if this field's value can be changed.

        Collection fields, and fields that are not part of the web
        service interface, are never modifiable. Read-only fields are
        not modifiable by external clients.

        :param is_external_client: Whether the code trying to modify
        the field is an external client. Read-only fields cannot be
        directly modified from external clients, but they might change
        as side effects of other changes.
        """
        if (ICollectionField.providedBy(field)
            or field.__name__.startswith('_')):
            return False
        if field.readonly:
            return not is_external_client
        return True

    def _unmarshallField(self, field_name, field):
        """See what a field would look like in a representation.

        :return: a 2-tuple (representation_name, representation_value).
        """
        cached_value = self._unmarshalled_field_cache.get(
            field_name, self.missing)
        if cached_value is not self.missing:
            return cached_value

        field = field.bind(self.context)
        marshaller = getMultiAdapter((field, self.request),
                                     IFieldMarshaller)
        try:
            if IUnmarshallingDoesntNeedValue.providedBy(marshaller):
                value = None
            else:
                value = getattr(self.entry, field_name)
            repr_value = marshaller.unmarshall(self.entry, value)
        except Unauthorized:
            # Either the client doesn't have permission to see
            # this field, or it doesn't have permission to read
            # its current value. Rather than denying the client
            # access to the resource altogether, use our special
            # 'redacted' tag: URI for the field's value.
            repr_value = self.REDACTED_VALUE

        unmarshalled = (marshaller.representation_name, repr_value)
        self._unmarshalled_field_cache[field_name] = unmarshalled
        return unmarshalled

    def _applyChanges(self, changeset):
        """Apply a dictionary of key-value pairs as changes to an entry.

        :param changeset: A dictionary. Should come from an incoming
        representation.

        :return: An error message to be propagated to the client.
        """
        changeset = copy.copy(changeset)
        validated_changeset = {}
        errors = []

        # The self link and resource type link aren't part of the
        # schema, so they're handled separately.
        modified_read_only_attribute = ("%s: You tried to modify a "
                                        "read-only attribute.")
        if 'self_link' in changeset:
            if changeset['self_link'] != canonical_url(self.context,
                                                       self.request):
                errors.append(modified_read_only_attribute % 'self_link')
            del changeset['self_link']

        if 'resource_type_link' in changeset:
            if changeset['resource_type_link'] != self.type_url:
                errors.append(modified_read_only_attribute %
                              'resource_type_link')
            del changeset['resource_type_link']

        if 'http_etag' in changeset:
            if changeset['http_etag'] != self.getETag(self.JSON_TYPE):
                errors.append(modified_read_only_attribute %
                              'http_etag')
            del changeset['http_etag']

        # For every field in the schema, see if there's a corresponding
        # field in the changeset.
        # Get the fields ordered by name so that we always evaluate them in
        # the same order. This is needed to predict errors when testing.
        for name, field in getFieldsInOrder(self.entry.schema):
            if name.startswith('_'):
                # This field is not part of the web service interface.
                continue
            field = field.bind(self.context)
            marshaller = getMultiAdapter((field, self.request),
                                         IFieldMarshaller)
            repr_name = marshaller.representation_name
            if not repr_name in changeset:
                # The client didn't try to set a value for this field.
                continue

            # Obtain the current value of the field, as it would be
            # shown in an outgoing representation. This gives us an easy
            # way to see if the client changed the value.
            try:
                current_value = marshaller.unmarshall(
                    self.entry, getattr(self.entry, name))
            except Unauthorized:
                # The client doesn't have permission to see the old
                # value. That doesn't necessarily mean they can't set
                # it to a new value, but it does mean we have to
                # assume they're changing it rather than see for sure
                # by comparing the old value to the new.
                current_value = self.REDACTED_VALUE

            # The client tried to set a value for this field. Marshall
            # it, validate it, and (if it's different from the current
            # value) move it from the client changeset to the
            # validated changeset.
            original_value = changeset.pop(repr_name)
            if original_value == current_value == self.REDACTED_VALUE:
                # The client can't see the field's current value, and
                # isn't trying to change it. Skip to the next field.
                continue

            try:
                value = marshaller.marshall_from_json_data(original_value)
            except (ValueError, ValidationError), e:
                errors.append("%s: %s" % (repr_name, e))
                continue

            if ICollectionField.providedBy(field):
                # This is a collection field, so the most we can do is set an
                # error message if the new value is not identical to the
                # current one.
                if value != current_value:
                    errors.append("%s: You tried to modify a collection "
                                  "attribute." % repr_name)
                continue

            if IBytes.providedBy(field):
                # We don't modify Bytes fields from the Entry that contains
                # them, but we may tell users how to do so if they attempt to
                # change them.
                if value != current_value:
                    if field.readonly:
                        errors.append(modified_read_only_attribute
                                      % repr_name)
                    else:
                        errors.append(
                            "%s: To modify this field you need to send a PUT "
                            "request to its URI (%s)."
                            % (repr_name, current_value))
                continue

            # If the new value is an object, make sure it provides the correct
            # interface.
            if value is not None and IObject.providedBy(field):
                # XXX leonardr 2008-04-12 spec=api-wadl-description:
                # This should be moved into the
                # ObjectLookupFieldMarshaller, once we make it
                # possible for Vocabulary fields to specify a schema
                # class the way IObject fields can.
                if value != None and not field.schema.providedBy(value):
                    errors.append("%s: Your value points to the "
                                  "wrong kind of object" % repr_name)
                    continue

            # Obtain the current value of the field.  This gives us an easy
            # way to see if the client changed the value.
            current_value = getattr(self.entry, name)

            change_this_field = True
            # Read-only attributes can't be modified. It's okay to specify a
            # value for an attribute that can't be modified, but the new value
            # must be the same as the current value.  This makes it possible
            # to GET a document, modify one field, and send it back.
            if field.readonly:
                change_this_field = False
                if value != current_value:
                    errors.append(modified_read_only_attribute
                                  % repr_name)
                    continue

            if change_this_field is True and value != current_value:
                if not IObject.providedBy(field):
                    # We don't validate IObject values because that
                    # can lead to infinite recursion. We don't _need_
                    # to validate IObject values because a client
                    # isn't changing anything about the IObject; it's
                    # just associating one IObject or another with an
                    # entry. We're already checking the type of the
                    # new IObject, and that's the only error the
                    # client can cause.
                    try:
                        # Do any field-specific validation.
                        field.validate(value)
                    except ConstraintNotSatisfied, e:
                        # Try to get a string error message out of
                        # the exception; otherwise use a generic message
                        # instead of whatever object the raise site
                        # thought would be a good idea.
                        if (len(e.args) > 0 and
                            isinstance(e.args[0], basestring)):
                            error = e.args[0]
                        else:
                            error = "Constraint not satisfied."
                        errors.append("%s: %s" % (repr_name, error))
                        continue
                    except (ValueError, ValidationError), e:
                        error = str(e)
                        if error == "":
                            error = "Validation error"
                        errors.append("%s: %s" % (repr_name, error))
                        continue
                validated_changeset[field] = (name, value)
        # If there are any fields left in the changeset, they're
        # fields that don't correspond to some field in the
        # schema. They're all errors.
        for invalid_field in changeset.keys():
            errors.append("%s: You tried to modify a nonexistent "
                          "attribute." % invalid_field)

        # If there were errors, display them and send a status of 400.
        if len(errors) > 0:
            self.request.response.setStatus(400)
            self.request.response.setHeader('Content-type', 'text/plain')
            return "\n".join(errors)

        # Make a snapshot of the entry to use in a notification event.
        entry_before_modification = Snapshot(
            self.entry.context, providing=providedBy(self.entry.context))

        # Store the entry's current URL so we can see if it changes.
        original_url = canonical_url(self.context, self.request)
        # Make the changes.
        for field, (name, value) in validated_changeset.items():
            field.set(self.entry, value)
            # Clear any marshalled value for this field from the
            # cache, so that the upcoming representation generation doesn't
            # use the cached value.
            if name in self._unmarshalled_field_cache:
                del(self._unmarshalled_field_cache[name])
        # The representation has changed, and etags will need to be
        # recalculated.
        self.etags_by_media_type = {}

        # Send a notification event.
        event = SQLObjectModifiedEvent(
            object=self.entry.context,
            object_before_modification=entry_before_modification,
            edited_fields=validated_changeset.keys(),
            user=getUtility(ILaunchBag).user)
        notify(event)

        # If the modification caused the entry's URL to change, tell
        # the client about the new URL.
        new_url = canonical_url(self.context, self.request)
        if new_url != original_url:
            self.request.response.setStatus(301)
            self.request.response.setHeader('Location', new_url)
            # RFC 2616 says the body of a 301 response, if present,
            # SHOULD be a note linking to the new object.
            return ''

        # If the object didn't move, serve up its representation.
        self.request.response.setHeader('Content-type', self.JSON_TYPE)
        return simplejson.dumps(self, cls=ResourceJSONEncoder)


class CollectionResource(ReadOnlyResource, BatchingResourceMixin,
                         CustomOperationResourceMixin):
    """A resource that serves a list of entry resources."""
    implements(ICollectionResource)

    def __init__(self, context, request):
        """Associate this resource with a specific object and request."""
        super(CollectionResource, self).__init__(context, request)
        self.collection = ICollection(context)

    def do_GET(self):
        """Fetch a collection and render it as JSON."""
        # Handle a custom operation, probably a search.
        operation_name = self.request.form.pop('ws.op', None)
        if operation_name is not None:
            result = self.handleCustomGET(operation_name)
            if isinstance(result, str) or isinstance(result, unicode):
                # The custom operation took care of everything and
                # just needs this string served to the client.
                return result
        else:
            # No custom operation was specified. Implement a standard
            # GET, which serves a JSON or WADL representation of the
            # collection.
            entries = self.collection.find()
            if entries is None:
                raise NotFound(self, self.collection_name)

            if self.getPreferredSupportedContentType() == self.WADL_TYPE:
                result = self.toWADL().encode("utf-8")
                self.request.response.setHeader(
                    'Content-Type', self.WADL_TYPE)
                return result

            result = self.batch(entries)

        self.request.response.setHeader('Content-type', self.JSON_TYPE)
        return simplejson.dumps(result, cls=ResourceJSONEncoder)

    def batch(self, entries=None):
        """Return a JSON representation of a batch of entries.

        :param entries: (Optional) A precomputed list of entries to batch.
        """
        if entries is None:
            entries = self.collection.find()
        result = super(CollectionResource, self).batch(entries, self.request)
        result['resource_type_link'] = self.type_url
        return result

    @property
    def type_url(self):
        "The URL to the resource type for the object."

        if IScopedCollection.providedBy(self.collection):
            # Scoped collection. The type URL depends on what type of
            # entry the collection holds.
            schema = self.context.relationship.value_type.schema
            adapter = EntryAdapterUtility.forSchemaInterface(schema)
            return adapter.entry_page_type_link
        else:
            # Top-level collection.
            schema = self.collection.entry_schema
            adapter = EntryAdapterUtility.forEntryInterface(schema)
            return adapter.collection_type_link


class ServiceRootResource(HTTPResource):
    """A resource that responds to GET by describing the service."""
    implements(IServiceRootResource, ICanonicalUrlData, IJSONPublishable)

    inside = None
    path = ''
    rootsite = None

    def __init__(self):
        """Initialize the resource.

        The service root constructor is different from other
        HTTPResource constructors because Zope initializes the object
        with no request or context, and then passes the request in
        when it calls the service root object.
        """
        # We're not calling the superclass constructor because
        # it assumes it's being called in the context of a particular
        # request.
        # pylint:disable-msg=W0231
        pass

    @property
    def request(self):
        """Fetch the current browser request."""
        return get_current_browser_request()

    def getETag(self, media_type):
        """Calculate an ETag for a representation of this resource.

        The service root resource changes only when the software
        itself changes. Thus, we can use the revision number itself as
        an ETag.
        """
        return '"%s-%s"' % (versioninfo.revno, media_type)

    def __call__(self, REQUEST=None):
        """Handle a GET request."""
        method = self.getRequestMethod(REQUEST)
        if method is None:
            result = self.HTTP_METHOD_OVERRIDE_ERROR
        elif method == "GET":
            result = self.do_GET()
        else:
            REQUEST.response.setStatus(405)
            REQUEST.response.setHeader("Allow", "GET")
            result = ""
        return self.applyTransferEncoding(result)

    def do_GET(self):
        """Describe the capabilities of the web service in WADL."""

        media_type = self.handleConditionalGET()
        if media_type is None:
            # The conditional GET succeeded. Serve nothing.
            return ""
        elif media_type == self.WADL_TYPE:
            result = self.toWADL().encode("utf-8")
        elif media_type == self.JSON_TYPE:
            # Serve a JSON map containing links to all the top-level
            # resources.
            result = simplejson.dumps(self, cls=ResourceJSONEncoder)

        self.request.response.setHeader('Content-Type', media_type)
        return result

    def toWADL(self):
        # Find all resource types.
        site_manager = zapi.getGlobalSiteManager()
        entry_classes = []
        collection_classes = []
        singular_names = {}
        plural_names = {}
        for registration in sorted(site_manager.registeredAdapters()):
            provided = registration.provided
            if IInterface.providedBy(provided):
                if (provided.isOrExtends(IEntry)
                    and IEntry.implementedBy(registration.factory)):
                    # The implementedBy check is necessary because
                    # some IEntry adapters aren't classes with
                    # schemas; they're functions. We can ignore these
                    # functions because their return value will be one
                    # of the classes with schemas, which we do describe.

                    # Make sure that no other entry class is using this
                    # class's singular or plural names.
                    schema = registration.required[0]
                    adapter = EntryAdapterUtility.forSchemaInterface(
                        schema)

                    singular = adapter.singular_type
                    assert not singular_names.has_key(singular), (
                        "Both %s and %s expose the singular name '%s'."
                        % (singular_names[singular].__name__,
                           schema.__name__, singular))
                    singular_names[singular] = schema

                    plural = adapter.plural_type
                    assert not plural_names.has_key(plural), (
                        "Both %s and %s expose the plural name '%s'."
                        % (plural_names[plural].__name__,
                           schema.__name__, plural))
                    plural_names[plural] = schema

                    entry_classes.append(registration.factory)
                elif (provided.isOrExtends(ICollection)
                      and ICollection.implementedBy(registration.factory)
                      and not IScopedCollection.implementedBy(
                        registration.factory)):
                    # See comment above re: implementedBy check.
                    # We omit IScopedCollection because those are handled
                    # by the entry classes.
                    collection_classes.append(registration.factory)
        template = LazrPageTemplateFile('../templates/wadl-root.pt')
        namespace = template.pt_getContext()
        namespace['context'] = self
        namespace['request'] = self.request
        namespace['entries'] = entry_classes
        namespace['collections'] = collection_classes
        return template.pt_render(namespace)

    def toDataForJSON(self):
        """Return a map of links to top-level collection resources.

        A top-level resource is one that adapts a utility.  Currently
        top-level entry resources (should there be any) are not
        represented.
        """
        type_url = "%s#%s" % (
            canonical_url(
                self.request.publication.getApplication(self.request),
                self.request),
            "service-root")
        data_for_json = {'resource_type_link' : type_url}
        publications = self.getTopLevelPublications()
        for link_name, publication in publications.items():
            data_for_json[link_name] = canonical_url(publication,
                                                     self.request)
        return data_for_json

    def getTopLevelPublications(self):
        """Return a mapping of top-level link names to published objects."""
        top_level_resources = {}
        site_manager = zapi.getGlobalSiteManager()
        # First, collect the top-level collections.
        for registration in site_manager.registeredAdapters():
            provided = registration.provided
            if IInterface.providedBy(provided):
                # XXX sinzui 2008-09-29 bug=276079:
                # Top-level collections need a marker interface
                # so that so top-level utilities are explicit.
                if (provided.isOrExtends(ICollection)
                     and ICollection.implementedBy(registration.factory)):
                    try:
                        utility = getUtility(registration.required[0])
                    except ComponentLookupError:
                        # It's not a top-level resource.
                        continue
                    entry_schema = registration.factory.entry_schema
                    if isinstance(entry_schema, property):
                        # It's not a top-level resource.
                        continue
                    adapter = EntryAdapterUtility.forEntryInterface(
                        entry_schema)
                    link_name = ("%s_collection_link" % adapter.plural_type)
                    top_level_resources[link_name] = utility
        # Now, collect the top-level entries.
        for utility in getAllUtilitiesRegisteredFor(ITopLevelEntryLink):
            link_name = ("%s_link" % utility.link_name)
            top_level_resources[link_name] = utility

        return top_level_resources

    @property
    def type_url(self):
        "The URL to the resource type for this resource."
        adapter = EntryAdapterUtility(self.entry.__class__)

        return "%s#%s" % (
            canonical_url(self.request.publication.getApplication(
                    self.request)),
            adapter.singular_type)


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

    @property
    def entry_schema(self):
        """The schema for the entries in this collection."""
        # We are given a model schema (IFoo). Look up the
        # corresponding entry schema (IFooEntry).
        model_schema = self.relationship.value_type.schema
        return zapi.getGlobalSiteManager().adapters.lookup1(
            model_schema, IEntry).schema

    def find(self):
        """See `ICollection`."""
        return self.collection


class RESTUtilityBase:

    def _service_root_url(self):
        """Return the URL to the service root."""
        request = get_current_browser_request()
        return canonical_url(request.publication.getApplication(request))


class EntryAdapterUtility(RESTUtilityBase):
    """Useful information about an entry's presence in the web service.

    This includes the links to entry's WADL resource type, and the
    resource type for a page of these entries.
    """

    @classmethod
    def forSchemaInterface(cls, entry_interface):
        """Create an entry adapter utility, given a schema interface.

        A schema interface is one that can be annotated to produce a
        subclass of IEntry.
        """
        entry_class = zapi.getGlobalSiteManager().adapters.lookup(
            (entry_interface,), IEntry)
        return EntryAdapterUtility(entry_class)

    @classmethod
    def forEntryInterface(cls, entry_interface):
        """Create an entry adapter utility, given a subclass of IEntry."""
        registrations = zapi.getGlobalSiteManager().registeredAdapters()
        entry_classes = [
            registration.factory for registration in registrations
            if (IInterface.providedBy(registration.provided)
                and registration.provided.isOrExtends(IEntry)
                and entry_interface.implementedBy(registration.factory))]
        assert not len(entry_classes) > 1, (
            "%s provides more than one IEntry subclass." %
            entry_interface.__name__)
        assert not len(entry_classes) < 1, (
            "%s does not provide any IEntry subclass." %
            entry_interface.__name__)
        return EntryAdapterUtility(entry_classes[0])

    def __init__(self, entry_class):
        """Initialize with a class that implements IEntry."""
        self.entry_class = entry_class

    @property
    def entry_interface(self):
        """The IEntry subclass implemented by this entry type."""
        interfaces = implementedBy(self.entry_class)
        entry_ifaces = [interface for interface in interfaces
                        if interface.extends(IEntry)]
        assert len(entry_ifaces) == 1, ("There must be one and only one "
                                        "IEntry implementation "
                                        "for %s" % self.entry_class)
        return entry_ifaces[0]

    @property
    def singular_type(self):
        """Return the singular name for this object type."""
        interface = self.entry_interface
        return interface.queryTaggedValue(LAZR_WEBSERVICE_NAME)['singular']

    @property
    def plural_type(self):
        """Return the plural name for this object type."""
        interface = self.entry_interface
        return interface.queryTaggedValue(LAZR_WEBSERVICE_NAME)['plural']

    @property
    def type_link(self):
        """The URL to the type definition for this kind of entry."""
        return "%s#%s" % (
            self._service_root_url(), self.singular_type)

    @property
    def collection_type_link(self):
        """The definition of a top-level collection of this kind of object."""
        return "%s#%s" % (
            self._service_root_url(), self.plural_type)

    @property
    def entry_page_type(self):
        """The definition of a collection of this kind of object."""
        return "%s-page-resource" % self.singular_type

    @property
    def entry_page_type_link(self):
        "The URL to the definition of a collection of this kind of object."
        return "%s#%s" % (
            self._service_root_url(), self.entry_page_type)

    @property
    def entry_page_representation_id(self):
        "The name of the description of a colleciton of this kind of object."
        return "%s-page" % self.singular_type

    @property
    def entry_page_representation_link(self):
        "The URL to the description of a collection of this kind of object."
        return "%s#%s" % (
            self._service_root_url(),
            self.entry_page_representation_id)

    @property
    def full_representation_link(self):
        """The URL to the description of the object's full representation."""
        return "%s#%s-full" % (
            self._service_root_url(), self.singular_type)
