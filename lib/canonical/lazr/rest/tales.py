# Copyright 2008 Canonical Ltd.  All rights reserved.
#
"""Implementation of the ws: namespace in TALES."""

__metaclass__ = type

import textwrap
import urllib

from epydoc.markup.restructuredtext import parse_docstring

from zope.app.zapi import getGlobalSiteManager
from zope.interface.interfaces import IInterface
from zope.publisher.interfaces.http import IHTTPApplicationRequest
from zope.schema import getFields
from zope.schema.interfaces import IChoice, IObject
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.publisher import get_current_browser_request

from canonical.lazr.enum import IEnumeratedType
from canonical.lazr.interfaces import (
    ICollection, ICollectionField, IEntry, IResourceGETOperation,
    IResourceOperation, IResourcePOSTOperation, IScopedCollection)
from canonical.lazr.rest import CollectionResource


class WadlAPI:

    """Base class for WADL-related function namespaces."""

    def _service_root_url(self):
        """Return the URL to the service root."""
        request = get_current_browser_request()
        return canonical_url(request.publication.getApplication(request))

    def _entry_adapter_for_schema(self, model_schema):
        entry_class = getGlobalSiteManager().adapters.lookup(
            (model_schema,), IEntry)
        return WadlEntryAdapterAPI(entry_class)

    def docstringToXHTML(self, doc):
        """Convert an epydoc docstring to XHTML."""
        if doc is None:
            return None
        doc = textwrap.dedent(doc)
        if doc == '':
            return None
        errors = []
        parsed = parse_docstring(doc, errors)
        if len(errors) > 0:
            messages = [str(error) for error in errors]
            raise AssertionError(
                "Invalid docstring %s:\n %s" % (doc, "\n ".join(messages)))
        return parsed.to_html(None)


class WadlResourceAPI(WadlAPI):
    "Namespace for WADL functions that operate on resources."

    def __init__(self, resource):
        "Initialize with a resource."
        self.resource = resource
        underlying_resource = removeSecurityProxy(resource)
        self.context = underlying_resource.context

    def url(self):
        """Return the full URL to the resource."""
        return canonical_url(self.context)


class WadlEntryResourceAPI(WadlResourceAPI):
    "Namespace for WADL functions that operate on entry resources."

    def __init__(self, entry_resource):
        "Initialize with an entry resource."
        super(WadlEntryResourceAPI, self).__init__(entry_resource)
        self.entry = self.resource.entry
        self.schema = self.entry.schema

    def type_link(self):
        "The URL to the resource type for the object."
        return "%s#%s" % (self._service_root_url(),
                          self.entry.__class__.__name__)


class WadlCollectionResourceAPI(WadlResourceAPI):
    "Namespace for WADL functions that operate on collection resources."

    def url(self):
        """The full URL to the resource.

        Scoped collections don't know their own URLs, so we have to
        figure it out for them here.
        """
        if IScopedCollection.providedBy(self.context):
            return (canonical_url(self.context.context) + '/' +
                    urllib.quote(self.context.relationship.__name__))
        else:
            return super(WadlCollectionResourceAPI, self).url()

    def type_link(self):
        "The URL to the resource type for the object."
        if IScopedCollection.providedBy(self.resource.collection):
            adapter = self._entry_adapter_for_schema(
                self.context.relationship.value_type.schema)
            return adapter.scoped_collection_type_link()
        else:
            collection_class = self.resource.collection.__class__
            adapter = WadlCollectionAdapterAPI(collection_class)
            return adapter.type_link()


class WadlServiceRootResourceAPI(WadlAPI):
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

    def url(self):
        """Return the full URL to the resource."""
        return self._service_root_url()

    def top_level_resources(self):
        """Return a list of dicts describing the top-level resources."""
        resource_dicts = []
        top_level = self.resource.getTopLevelPublications()
        for link_name, publication in top_level.items():
            # We only expose collection resources for now.
            resource = CollectionResource(publication, self.resource.request)
            resource_dicts.append({'name' : link_name,
                                   'path' : "$['%s']" % link_name,
                                   'resource' : resource})
        return resource_dicts


class WadlResourceAdapterAPI(WadlAPI):
    """Namespace for functions that operate on resource adapter classes."""

    def __init__(self, adapter, adapter_interface):
        "Initialize with an adapter class."
        self.adapter = adapter
        self.adapter_interface = adapter_interface

    def doc(self):
        """Human-readable XHTML documentation for this object type."""
        return self.docstringToXHTML(self.adapter.__doc__)

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
            reg for reg in getGlobalSiteManager().registrations()
            if (IInterface.providedBy(reg.provided)
                and reg.provided.isOrExtends(self.adapter_interface)
                and reg.value == self.adapter)]
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
            (model_class, IHTTPApplicationRequest), IResourceOperation)
        ops = [{'name' : name, 'op' : op} for name, op in operations]
        return ops


class WadlEntryAdapterAPI(WadlResourceAdapterAPI):
    """Namespace for WADL functions that operate on entry adapter classes.

    The entry adapter class is used to describe entries of a certain
    type, and scoped collections full of entries of that type.
    """

    def __init__(self, adapter):
        super(WadlEntryAdapterAPI, self).__init__(adapter, IEntry)

    def singular_type(self):
        """Return the singular name for this object type."""
        return self.adapter.__name__

    def type_link(self):
        """The URL to the type definition for this kind of resource."""
        return "%s#%s" % (
            self._service_root_url(), self.singular_type())

    def full_representation_link(self):
        """The URL to the description of the object's full representation."""
        return "%s#%s-full" % (
            self._service_root_url(), self.singular_type())

    def patch_representation_link(self):
        """The URL to the description of the object's patch representation."""
        return "%s#%s-diff" % (
            self._service_root_url(), self.singular_type())

    def entry_page_representation_link(self):
        return "%s#%s" % (
            self._service_root_url(),
            self.entry_page_representation_id())

    def scoped_collection_type(self):
        return "%s-scoped-collection" % self.singular_type()

    def scoped_collection_type_link(self):
        return "%s#%s" % (
            self._service_root_url(), self.scoped_collection_type())

    def entry_page_representation_id(self):
        return "%s-page" % self.singular_type()

    def all_fields(self):
        "Return all schema fields for the object."
        return getFields(self.adapter.schema).values()

    def all_writable_fields(self):
        """Return all writable schema fields for the object.

        Read-only fields and collections are excluded.
        """
        return [field for field in self.all_fields()
                if (not ICollectionField.providedBy(field)
                    or field.readonly)]


class WadlCollectionAdapterAPI(WadlResourceAdapterAPI):
    "Namespace for WADL functions that operate on collection adapters."

    def __init__(self, adapter):
        super(WadlCollectionAdapterAPI, self).__init__(adapter, ICollection)

    def collection_type(self):
        """The name of this kind of resource."""
        return self.adapter.__name__

    def type_link(self):
        "The URL to the resource type for the object."
        return "%s#%s" % (self._service_root_url(),
                          self.collection_type())

    def entry_schema(self):
        return self.adapter.entry_schema


class WadlFieldAPI(WadlAPI):
    "Namespace for WADL functions that operate on schema fields."

    def __init__(self, field):
        """Initialize with a field."""
        self.field = field

    def name(self):
        """The name of this field."""
        name = self.field.__name__
        if ICollectionField.providedBy(self.field):
            return name + '_collection_link'
        elif IObject.providedBy(self.field):
            return name + '_link'
        else:
            return name

    def doc(self):
        """The docstring for this field."""
        title = self.field.title
        if title != '':
            title = "<strong>%s</strong>" % title
            if self.field.description != '':
                return "%s: %s" % (self.field.title, self.field.description)
            else:
                return title
        return self.field.description

    def path(self):
        """The JSONPath path to this field within a JSON document."""
        return "$['%s']" % self.name()

    def is_link(self):
        """Is this field a link to another resource?"""
        return (IObject.providedBy(self.field) or
                ICollectionField.providedBy(self.field))

    def type_link(self):
        """The URL of the description of the type this field is a link to."""
        if ICollectionField.providedBy(self.field):
            schema = self.field.value_type.schema
        elif IObject.providedBy(self.field):
            schema = self.field.schema
        else:
            raise AssertionError("Field is not a link to another resource.")
        adapter = self._entry_adapter_for_schema(schema)

        if ICollectionField.providedBy(self.field):
            return adapter.scoped_collection_type_link()
        else:
            return adapter.type_link()


    def options(self):
        """An enumeration of acceptable values for this field.

        :return: An iterable of Items if the field implements IChoice
            and its vocabulary implements IEnumeratedType. Otherwise, None.
        """
        if (IChoice.providedBy(self.field) and
            IEnumeratedType.providedBy(self.field.vocabulary)):
            return self.field.vocabulary.items
        return None


class WadlOperationAPI(WadlAPI):
    "Namespace for WADL functions that operate on named operations."

    def __init__(self, operation):
        """Initialize with an operation."""
        self.operation = operation

    def http_method(self):
        """The HTTP method used to invoke this operation."""
        if IResourceGETOperation.implementedBy(self.operation):
            return "GET"
        elif IResourcePOSTOperation.implementedBy(self.operation):
            return "POST"
        else:
            raise AssertionError("Named operations must use GET or POST.")

    def doc(self):
        return self.docstringToXHTML(self.operation.__doc__)
