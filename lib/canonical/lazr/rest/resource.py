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

import copy
from datetime import datetime
import simplejson

from zope.app import zapi
from zope.app.pagetemplate.engine import TrustedAppPT
from zope.component import adapts, getAdapters, getMultiAdapter, getUtility
from zope.component.interfaces import ComponentLookupError
from zope.interface import implements
from zope.interface.interfaces import IInterface
from zope.pagetemplate.pagetemplatefile import PageTemplateFile
from zope.proxy import isProxy
from zope.publisher.interfaces import NotFound
from zope.schema import ValidationError, getFields
from zope.schema.interfaces import (
    ConstraintNotSatisfied, IBytes, IChoice, IObject)
from zope.security.proxy import removeSecurityProxy
from canonical.lazr.enum import BaseItem

# XXX leonardr 2008-01-25 bug=185958:
# canonical_url and BatchNavigator code should be moved into lazr.
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData
from canonical.launchpad.webapp.publisher import get_current_browser_request
from canonical.lazr.interfaces import (
    ICollection, ICollectionField, ICollectionResource, IEntry,
    IEntryResource, IFieldMarshaller, IHTTPResource, IJSONPublishable,
    IResourceGETOperation, IResourcePOSTOperation, IScopedCollection,
    IServiceRootResource)
from canonical.launchpad.webapp.vocabulary import SQLObjectVocabularyBase
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
        if result is None:
            return ""

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
            field = field.bind(self.context)
            marshaller = getMultiAdapter((field, self.request),
                                          IFieldMarshaller)
            repr_name = marshaller.representationName(name)
            repr_value = marshaller.unmarshall(self.entry, name, value)
            data[repr_name] = repr_value
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
            if self.getPreferredSupportedContentType() == self.WADL_TYPE:
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
            field = field.bind(self.context)
            marshaller = getMultiAdapter((field, self.request),
                                         IFieldMarshaller)
            repr_name = marshaller.representationName(name)
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

    def _applyChanges(self, changeset):
        """Apply a dictionary of key-value pairs as changes to an entry.

        :param changeset: A dictionary. Should come from an incoming
        representation.

        :return: An error message to be propagated to the client.
        """
        changeset = copy.copy(changeset)
        validated_changeset = {}
        errors = []

        # The self link isn't part of the schema, so it's
        # handled separately.
        if 'self_link' in changeset:
            if changeset['self_link'] != canonical_url(self.context):
                errors.append("self_link: You tried to modify "
                              "a read-only attribute.")
            del(changeset['self_link'])

        # For every field in the schema, see if there's a corresponding
        # field in the changeset.
        for name, field in getFields(self.entry.schema).items():
            if name.startswith('_'):
                # This field is not part of the web service interface.
                continue
            field = field.bind(self.context)
            marshaller = getMultiAdapter((field, self.request),
                                         IFieldMarshaller)
            repr_name = marshaller.representationName(name)
            if not repr_name in changeset:
                # The client didn't try to set a value for this field.
                continue

            # The client tried to set a value for this field. Marshall
            # it, validate it, and move it from the client changeset
            # to the validated changeset.
            value = changeset[repr_name]
            del(changeset[repr_name])

            if ICollectionField.providedBy(field):
                # This is a collection field, so the most we can do is set an
                # error message if the new value is not identical to the
                # current one.
                current_unmarshalled_value = marshaller.unmarshall(
                    self.entry, name, getattr(self.entry, name))
                if value != current_unmarshalled_value:
                    errors.append("%s: You tried to modify a collection "
                                  "attribute." % repr_name)
                continue

            if IBytes.providedBy(field):
                # We don't modify Bytes fields from the Entry that contains
                # them, but we may tell users how to do so if they attempt to
                # change them.
                current_unmarshalled_value = marshaller.unmarshall(
                    self.entry, name, getattr(self.entry, name))
                if value != current_unmarshalled_value:
                    if field.readonly:
                        errors.append("%s: You tried to modify a read-only "
                                      "attribute." % repr_name)
                    else:
                        errors.append(
                            "%s: To modify this field you need to send a PUT "
                            "request to its URI (%s)."
                            % (repr_name, current_unmarshalled_value))
                continue

            try:
                value = marshaller.marshall(value)
            except (ValueError, ValidationError), e:
                errors.append("%s: %s" % (repr_name, e))
                continue

            # If the new value is an object, make sure it provides the correct
            # interface.
            if value is not None and IObject.providedBy(field):
                # XXX leonardr 2008-15-04 blueprint=api-wadl-description:
                # This should be moved into the
                # ObjectLookupFieldMarshaller, once we make it
                # possible for Vocabulary fields to specify a schema
                # class the way IObject fields can.
                if not field.schema.providedBy(value):
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
                    errors.append("%s: You tried to modify a read-only "
                                  "attribute." % repr_name)
                    continue

            if change_this_field is True and value != current_value:
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
                validated_changeset[name] = value
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
            result = self.batch(entries, self.request)

        self.request.response.setHeader('Content-type', self.JSON_TYPE)
        return simplejson.dumps(result, cls=ResourceJSONEncoder)


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

    def __call__(self, REQUEST=None):
        """Handle a GET request."""
        if REQUEST.method == "GET":
            return self.do_GET()
        else:
            REQUEST.response.setStatus(405)
            REQUEST.response.setHeader("Allow", "GET")

    def do_GET(self):
        """Describe the capabilities of the web service in WADL."""

        if self.getPreferredSupportedContentType() == self.WADL_TYPE:
            result = self.toWADL().encode("utf-8")
            self.request.response.setHeader('Content-Type', self.WADL_TYPE)
            return result

        # The client didn't want WADL, so we'll give them JSON.
        # Specifically, a JSON map containing links to all the
        # top-level resources.
        self.request.response.setHeader('Content-type', self.JSON_TYPE)
        return simplejson.dumps(self, cls=ResourceJSONEncoder)

    def toWADL(self):
        # Find all resource types.
        site_manager = zapi.getGlobalSiteManager()
        entry_classes = []
        collection_classes = []
        for registration in site_manager.registrations():
            provided = registration.provided
            if IInterface.providedBy(provided):
                if (provided.isOrExtends(IEntry)
                    and IEntry.implementedBy(registration.value)):
                    # The implementedBy check is necessary because
                    # some IEntry adapters aren't classes with
                    # schemas; they're functions. We can ignore these
                    # functions because their return value will be one
                    # of the classes with schemas, which we do describe.
                    entry_classes.append(registration.value)
                elif (provided.isOrExtends(ICollection)
                      and ICollection.implementedBy(registration.value)
                      and not IScopedCollection.implementedBy(
                        registration.value)):
                    # See comment above re: implementedBy check.
                    # We omit IScopedCollection because those are handled
                    # by the entry classes.
                    collection_classes.append(registration.value)
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
        data_for_json = {}
        publications = self.getTopLevelPublications()
        for link_name, publication in publications.items():
            data_for_json[link_name] = canonical_url(publication)
        return data_for_json

    def getTopLevelPublications(self):
        """Return a mapping of top-level link names to published objects.

        This method assumes that only collections are exposed at the top
        level.
        """
        top_level_resources = {}
        site_manager = zapi.getGlobalSiteManager()
        for registration in site_manager.registrations():
            provided = registration.provided
            if IInterface.providedBy(provided):
                if (provided.isOrExtends(ICollection)
                     and ICollection.implementedBy(registration.value)):
                    try:
                        utility = getUtility(registration.required[0])
                    except ComponentLookupError:
                        # It's not a top-level resource.
                        continue
                    link_name = ("%s_collection_link"
                                 % registration.value.__name__)
                    top_level_resources[link_name] = utility
        return top_level_resources


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
