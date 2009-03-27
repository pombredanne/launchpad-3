# Copyright 2008 Canonical Ltd.  All rights reserved.
#
"""Implementation of the ws: namespace in TALES."""

__metaclass__ = type

all = ['entry_adapter_for_schema']

import simplejson
import textwrap
import urllib

from epydoc.markup import DocstringLinker
from epydoc.markup.restructuredtext import parse_docstring

from zope.app.zapi import getGlobalSiteManager
from zope.component import adapts, queryAdapter
from zope.interface import implements
from zope.interface.interfaces import IInterface
from zope.schema import getFieldsInOrder
from zope.schema.interfaces import IBytes, IChoice, IDate, IDatetime, IObject
from zope.security.proxy import removeSecurityProxy
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.traversing.browser import absoluteURL
from zope.traversing.interfaces import IPathAdapter
from lazr.enum import IEnumeratedType

from canonical.lazr.rest import EntryResource, ResourceJSONEncoder
from canonical.lazr.interfaces import (
    ICollection, IEntry, IJSONRequestCache, IResourceGETOperation,
    IResourceOperation, IResourcePOSTOperation, IScopedCollection,
    ITopLevelEntryLink)
from canonical.lazr.interfaces.fields import (
    ICollectionField, IReferenceChoice)
from canonical.lazr.interfaces.rest import (
    IWebServiceClientRequest, LAZR_WEBSERVICE_NAME)
from canonical.lazr.rest import (
    CollectionResource, EntryAdapterUtility, IObjectLink, RESTUtilityBase)
from canonical.lazr.utils import get_current_browser_request


class WadlDocstringLinker(DocstringLinker):
    """DocstringLinker used during WADL geneneration.

    epydoc uses this object to turn index and identifier references
    like `DocstringLinker` into an appropriate markup in the output
    format.

    We don't want to generate links in the WADL file so we basically
    return the identifier without any special linking markup.
    """

    def translate_identifier_xref(self, identifier, label=None):
        """See `DocstringLinker`."""
        if label:
            return label
        return identifier

    def translate_indexterm(self, indexterm):
        """See `DocstringLinker`."""
        return indexterm


WADL_DOC_TEMPLATE = (
    '<wadl:doc xmlns="http://www.w3.org/1999/xhtml">\n%s\n</wadl:doc>')


def generate_wadl_doc(doc):
    """Create a wadl:doc element wrapping a docstring."""
    if doc is None:
        return None
    # Our docstring convention prevents dedent from working correctly, we need
    # to dedent all but the first line.
    lines = doc.strip().splitlines()
    if not len(lines):
        return None
    doc = "%s\n%s" % (lines[0], textwrap.dedent("\n".join(lines[1:])))
    errors = []
    parsed = parse_docstring(doc, errors)
    if len(errors) > 0:
        messages = [str(error) for error in errors]
        raise AssertionError(
            "Invalid docstring %s:\n %s" % (doc, "\n ".join(messages)))

    return WADL_DOC_TEMPLATE % parsed.to_html(WadlDocstringLinker())


class WebServiceRequestAPI:
    """Namespace for web service functions related to a website request."""
    implements(IPathAdapter)
    adapts(IBrowserRequest)

    def __init__(self, request):
        """Initialize with respect to a request."""
        self.request = request

    def cache(self):
        """Return the request's IJSONRequestCache."""
        return IJSONRequestCache(self.request)


class WebLayerAPI:
    """Namespace for web service functions used in the website.

    These functions are used to prepopulate a client cache with JSON
    representations of resources.
    """

    def __init__(self, context):
        self.context = context

    @property
    def is_entry(self):
        """Whether the object is published as an entry."""
        return queryAdapter(self.context, IEntry) != None

    @property
    def json(self):
        """Return a JSON description of the object."""
        request = IWebServiceClientRequest(get_current_browser_request())
        if queryAdapter(self.context, IEntry):
            resource = EntryResource(self.context, request)
        else:
            # Just dump it as JSON.
            resource = self.context
        return simplejson.dumps(resource, cls=ResourceJSONEncoder)


class WadlResourceAPI(RESTUtilityBase):
    "Namespace for WADL functions that operate on resources."

    def __init__(self, resource):
        "Initialize with a resource."
        self.resource = resource
        underlying_resource = removeSecurityProxy(resource)
        self.context = underlying_resource.context

    @property
    def url(self):
        """Return the full URL to the resource."""
        return absoluteURL(self.context, get_current_browser_request())


class WadlEntryResourceAPI(WadlResourceAPI):
    "Namespace for WADL functions that operate on entry resources."

    def __init__(self, entry_resource):
        "Initialize with an entry resource."
        super(WadlEntryResourceAPI, self).__init__(entry_resource)
        self.entry = self.resource.entry
        self.schema = self.entry.schema

    @property
    def type_link(self):
        return self.resource.type_url

    @property
    def fields_with_values(self):
        """Return all of this entry's Field objects."""
        fields = []
        for name, field in getFieldsInOrder(self.schema):
            fields.append({'field' : field, 'value': "foo"})
        return fields


class WadlCollectionResourceAPI(WadlResourceAPI):
    "Namespace for WADL functions that operate on collection resources."

    @property
    def url(self):
        """The full URL to the resource.

        Scoped collections don't know their own URLs, so we have to
        figure it out for them here.
        """
        if IScopedCollection.providedBy(self.context):
            # Check whether the field has been exported with a different name
            # and use that if so.
            webservice_tag = self.context.relationship.queryTaggedValue(
                'lazr.webservice.exported')
            if webservice_tag is not None:
                relationship_name = webservice_tag['as']
            else:
                relationship_name = self.context.relationship.__name__
            return (absoluteURL(self.context.context,
                                get_current_browser_request()) + '/' +
                    urllib.quote(relationship_name))
        else:
            return super(WadlCollectionResourceAPI, self).url

    @property
    def type_link(self):
        "The URL to the resource type for the object."
        return self.resource.type_url


class WadlByteStorageResourceAPI(WadlResourceAPI):
    """Namespace for functions that operate on byte storage resources."""

    def type_link(self):
        "The URL to the resource type for the object."
        return "%s#HostedFile" % self._service_root_url()


class WadlServiceRootResourceAPI(RESTUtilityBase):
    """Namespace for functions that operate on the service root resource.

    This class doesn't subclass WadlResourceAPI because that class
    assumes there's an underlying 'context' object that's being
    published. The service root resource is unique in not having a
    'context'. Methods like url() need to be implemented specially
    with that in mind.
    """

    def __init__(self, resource):
        """Initialize the helper class with a resource."""
        self.resource = resource

    @property
    def url(self):
        """Return the full URL to the resource."""
        return self._service_root_url()

    @property
    def top_level_resources(self):
        """Return a list of dicts describing the top-level resources."""
        resource_dicts = []
        top_level = self.resource.getTopLevelPublications()
        for link_name, publication in top_level.items():
            if ITopLevelEntryLink.providedBy(publication):
                # It's a link to an entry resource.
                resource = publication
            else:
                # It's a collection resource.
                resource = CollectionResource(
                    publication, self.resource.request)
            resource_dicts.append({'name' : link_name,
                                   'path' : "$['%s']" % link_name,
                                   'resource' : resource})
        return resource_dicts


class WadlResourceAdapterAPI(RESTUtilityBase):
    """Namespace for functions that operate on resource adapter classes."""

    def __init__(self, adapter, adapter_interface):
        "Initialize with an adapter class."
        self.adapter = adapter
        self.adapter_interface = adapter_interface

    @property
    def doc(self):
        """Human-readable XHTML documentation for this object type."""
        return generate_wadl_doc(self.adapter.__doc__)

    @property
    def named_operations(self):
        """Return all named operations registered on the resource.

        :return: a dict containing 'name' and 'op' keys. 'name' is the
            name of the operation and 'op' is the ResourceOperation
            object.
        """
        # Our 'adapter' is the resource adapter class, generated with
        # reference to some underlying model class. Named operations
        # are registered in ZCML under the model class. To find them,
        # we need to locate the model class that our 'adapter' is
        # adapting.
        registrations = [
            reg for reg in getGlobalSiteManager().registeredAdapters()
            if (IInterface.providedBy(reg.provided)
                and reg.provided.isOrExtends(self.adapter_interface)
                and reg.factory == self.adapter)]
        # If there's more than one model class (because the 'adapter' was
        # registered to adapt more than one model class to ICollection or
        # IEntry), we don't know which model class to search for named
        # operations. Treat this as an error.
        if len(registrations) != 1:
            raise AssertionError(
                "There must be one (and only one) adapter from %s to %s." % (
                    self.adapter.__name__,
                    self.adapter_interface.__name__))
        model_class = registrations[0].required[0]
        operations = getGlobalSiteManager().adapters.lookupAll(
            (model_class, IWebServiceClientRequest), IResourceOperation)
        ops = [{'name' : name, 'op' : op} for name, op in operations]
        return ops


class WadlEntryInterfaceAdapterAPI(WadlResourceAdapterAPI):
    """Namespace for WADL functions that operate on entry interfaces.

    That is, IEntry subclasses.
    """
    def __init__(self, entry_interface):
        super(WadlEntryInterfaceAdapterAPI, self).__init__(
            entry_interface, IEntry)
        self.utility = EntryAdapterUtility.forEntryInterface(entry_interface)

    @property
    def entry_page_representation_link(self):
        "The URL to the description of a collection of this kind of object."
        return self.utility.entry_page_representation_link


class WadlEntryAdapterAPI(WadlResourceAdapterAPI):
    """Namespace for WADL functions that operate on entry adapter classes.

    The entry adapter class is used to describe entries of a certain
    type, and scoped collections full of entries of that type.
    """

    def __init__(self, adapter):
        super(WadlEntryAdapterAPI, self).__init__(adapter, IEntry)
        self.utility = EntryAdapterUtility(adapter)

    @property
    def singular_type(self):
        """Return the singular name for this object type."""
        return self.utility.singular_type

    @property
    def type_link(self):
        """The URL to the type definition for this kind of resource."""
        return self.utility.type_link

    @property
    def full_representation_link(self):
        """The URL to the description of the object's full representation."""
        return self.utility.full_representation_link

    @property
    def patch_representation_link(self):
        """The URL to the description of the object's patch representation."""
        return "%s#%s-diff" % (
            self._service_root_url(), self.singular_type)

    @property
    def entry_page_type(self):
        """The definition of a collection of this kind of object."""
        return self.utility.entry_page_type

    @property
    def entry_page_type_link(self):
        "The URL to the definition of a collection of this kind of object."
        return self.utility.entry_page_type_link

    @property
    def entry_page_representation_id(self):
        "The name of the description of a colleciton of this kind of object."
        return self.utility.entry_page_representation_id

    @property
    def all_fields(self):
        "Return all schema fields for the object."
        return [field for name, field in
                getFieldsInOrder(self.adapter.schema)]

    @property
    def all_writable_fields(self):
        """Return all writable schema fields for the object.

        Read-only fields and collections are excluded.
        """
        return [field for field in self.all_fields
                if not (ICollectionField.providedBy(field) or field.readonly)]


class WadlCollectionAdapterAPI(WadlResourceAdapterAPI):
    "Namespace for WADL functions that operate on collection adapters."

    def __init__(self, adapter):
        super(WadlCollectionAdapterAPI, self).__init__(adapter, ICollection)

    @property
    def collection_type(self):
        """The name of this kind of resource."""
        tag = self.entry_schema.queryTaggedValue(LAZR_WEBSERVICE_NAME)
        return tag['plural']

    @property
    def type_link(self):
        "The URL to the resource type for the object."
        return "%s#%s" % (self._service_root_url(),
                          self.collection_type)

    @property
    def entry_schema(self):
        """The schema interface for the kind of entry in this collection."""
        return self.adapter.entry_schema


class WadlFieldAPI(RESTUtilityBase):
    "Namespace for WADL functions that operate on schema fields."

    def __init__(self, field):
        """Initialize with a field."""
        self.field = field

    @property
    def required(self):
        """An xsd:bool value for whether or not this field is required."""
        if self.field.required:
            return 'true'
        else:
            return 'false'

    @property
    def name(self):
        """The name of this field."""
        # It would be nice to farm this out to IFieldMarshaller, but
        # IFieldMarshaller can't be instantiated except on a field
        # that's been bound to an object. Here there's no object since
        # we're doing introspection on the class. A possible solution is
        # to split IFieldMarshaller.representation_name() into a
        # separate interface.

        name = self.field.__name__
        if ICollectionField.providedBy(self.field):
            return name + '_collection_link'
        elif (IObject.providedBy(self.field) or IBytes.providedBy(self.field)
              or IReferenceChoice.providedBy(self.field)):
            return name + '_link'
        else:
            return name

    @property
    def doc(self):
        """The docstring for this field."""
        return generate_wadl_doc(self.field.__doc__)

    @property
    def path(self):
        """The JSONPath path to this field within a JSON document."""
        return "$['%s']" % self.name

    @property
    def type(self):
        """The XSD type of this field."""
        if IDatetime.providedBy(self.field):
            return 'xsd:dateTime'
        elif IDate.providedBy(self.field):
            return 'xsd:date'
        else:
            return None

    @property
    def is_link(self):
        """Does this field have real data or is it just a link?"""
        return IObjectLink.providedBy(self.field)

    @property
    def is_represented_as_link(self):
        """Is this field represented as a link to another resource?"""
        return (IObject.providedBy(self.field) or
                IReferenceChoice.providedBy(self.field) or
                ICollectionField.providedBy(self.field) or
                IBytes.providedBy(self.field) or
                self.is_link)

    @property
    def type_link(self):
        """The URL of the description of the type this field is a link to."""
        # Handle externally-hosted binary documents.
        if IBytes.providedBy(self.field):
            return "%s#HostedFile" % self._service_root_url()

        # Handle entries and collections of entries.
        utility = self._entry_adapter_utility
        if ICollectionField.providedBy(self.field):
            return utility.entry_page_type_link
        else:
            return utility.type_link

    @property
    def representation_link(self):
        """The URL of the description of the representation of this field."""
        utility = self._entry_adapter_utility
        if ICollectionField.providedBy(self.field):
            return utility.entry_page_representation_link
        else:
            return utility.full_representation_link

    @property
    def _entry_adapter_utility(self):
        """Find an entry adapter for this field."""
        if ICollectionField.providedBy(self.field):
            schema = self.field.value_type.schema
        elif (IObject.providedBy(self.field)
              or IObjectLink.providedBy(self.field)
              or IReferenceChoice.providedBy(self.field)):
            schema = self.field.schema
        else:
            raise TypeError("Field is not of a supported type.")
        assert schema is not IObject, (
            "Null schema provided for %s" % self.field.__name__)
        return EntryAdapterUtility.forSchemaInterface(schema)


    @property
    def options(self):
        """An enumeration of acceptable values for this field.

        :return: An iterable of Items if the field implements IChoice
            and its vocabulary implements IEnumeratedType. Otherwise, None.
        """
        if (IChoice.providedBy(self.field) and
            IEnumeratedType.providedBy(self.field.vocabulary)):
            return self.field.vocabulary.items
        return None


class WadlTopLevelEntryLinkAPI(RESTUtilityBase):
    """Namespace for WADL functions that operate on top-level entry links."""

    def __init__(self, entry_link):
        self.entry_link = entry_link

    def type_link(self):
        return EntryAdapterUtility.forSchemaInterface(
            self.entry_link.entry_type).type_link


class WadlOperationAPI(RESTUtilityBase):
    "Namespace for WADL functions that operate on named operations."

    def __init__(self, operation):
        """Initialize with an operation."""
        self.operation = operation

    @property
    def http_method(self):
        """The HTTP method used to invoke this operation."""
        if IResourceGETOperation.implementedBy(self.operation):
            return "GET"
        elif IResourcePOSTOperation.implementedBy(self.operation):
            return "POST"
        else:
            raise AssertionError("Named operations must use GET or POST.")

    @property
    def is_get(self):
        """Whether or not the operation is a GET operation."""
        return self.http_method == "GET"

    @property
    def doc(self):
        """Human-readable documentation for this operation."""
        return generate_wadl_doc(self.operation.__doc__)

    @property
    def has_return_type(self):
        """Does this operation declare a return type?"""
        return_field = getattr(self.operation, 'return_type', None)
        return return_field is not None

    @property
    def returns_link(self):
        """Does this operation return a link to an object?"""
        return_field = getattr(self.operation, 'return_type', None)
        if return_field is not None:
            field_adapter = WadlFieldAPI(return_field)
            return field_adapter.is_link
        return False

    @property
    def return_type_resource_type_link(self):
        """Link to the description of this operation's return value."""
        return_field = getattr(self.operation, 'return_type', None)
        if return_field is not None:
            field_adapter = WadlFieldAPI(return_field)
            try:
                return field_adapter.type_link
            except TypeError:
                # The operation does not return any object exposed
                # through the web service.
                pass
        return None

    @property
    def return_type_representation_link(self):
        """Link to the representation of this operation's return value."""
        return_field = getattr(self.operation, 'return_type', None)
        if return_field is not None:
            field_adapter = WadlFieldAPI(return_field)
            try:
                return field_adapter.representation_link
            except TypeError:
                # The operation does not return any object exposed
                # through the web service.
                pass
        return None
