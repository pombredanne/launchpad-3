# Copyright 2008 Canonical Ltd.  All rights reserved.
#
"""Implementation of the ws: namespace in TALES."""

__metaclass__ = type

from zope.app.zapi import getGlobalSiteManager
from zope.publisher.interfaces.http import IHTTPApplicationRequest
from zope.schema import getFields
from zope.schema.interfaces import IChoice, IObject
from zope.interface.declarations import providedBy
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp import canonical_url

from canonical.lazr.enum import IEnumeratedType
from canonical.lazr.interfaces import (
    ICollectionField, IResourceGETOperation, IResourceOperation,
    IResourcePOSTOperation)


class WadlResourceAPI:
    "Namespace for WADL functions that operate on resources."

    def __init__(self, resource):
        "Initialize with a resource."
        self.resource = resource
        underlying_resource = removeSecurityProxy(resource)
        self.context = underlying_resource.context

    def url(self):
        """Return the full URL to the resource."""
        return canonical_url(self.context)

    def named_operations(self):
        """Return all named operations registered on the resource.

        :return: a dict containing 'name' and 'op' keys. 'name' is the
            name of the operation and 'op' is the ResourceOperation
            object.
        """
        operations = getGlobalSiteManager().adapters.lookupAll(
            (providedBy(self.context), IHTTPApplicationRequest),
            IResourceOperation)
        ops = [{'name' : name, 'op' : op} for name, op in operations]
        return ops


class WadlEntryResourceAPI(WadlResourceAPI):
    "Namespace for WADL functions that operate on entry resources."

    def __init__(self, entry_resource):
        "Initialize with an entry resource."
        super(WadlEntryResourceAPI, self).__init__(entry_resource)
        self.entry = self.resource.entry
        self.schema = self.entry.schema

    def singular_type(self):
        "Return the singular name for this object type."
        return self.entry.__class__.__name__

    def type_link(self):
        "The URL to the resource type for the object."
        # Right now the resource type is defined in the same file
        # as the resource, so a relative link is fine. This won't
        # always be so.
        return "#" + self.singular_type()

    def full_representation_link(self):
        "The URL to the description of the object's full representation."
        # Right now the resource type is defined in the same file
        # as the resource, so a relative link is fine. This won't
        # always be so.
        return "#" + self.singular_type() + '-full'

    def patch_representation_link(self):
        "The URL to the description of the object's full representation."
        # Right now the resource type is defined in the same file
        # as the resource, so a relative link is fine. This won't
        # always be so.
        return "#" + self.singular_type() + '-diff'

    def all_fields(self):
        "Return all schema fields for the object."
        return getFields(self.schema).values()

    def all_writable_fields(self):
        """Return all writable schema fields for the object.

        Read-only fields and collections are excluded.
        """
        return [field for field in self.all_fields()
                if (not ICollectionField.providedBy(field)
                    or field.readonly)]

class WadlFieldAPI:
    "Namespace for WADL functions that operate on schema fields."

    def __init__(self, field):
        "Initialize with a field."
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

    def path(self):
        """The 'path' to this field within a JSON document.

        This is just a string that looks like Python code you'd write
        to do a dictionary lookup. There's no XPath-like standard for
        JSON so we made something up that seems JSONic.
        """
        return '["%s"]' % self.name()

    def is_link(self):
        "Is this field a link to another resource?"
        return (IObject.providedBy(self.field) or
                ICollectionField.providedBy(self.field))

    def options(self):
        """An enumeration of acceptable values for this field.

        :return: An iterable of Items if the field implements IChoice
            and its vocabulary implements IEnumeratedType. Otherwise, None.
        """
        if (IChoice.providedBy(self.field) and
            IEnumeratedType.providedBy(self.field.vocabulary)):
            return self.field.vocabulary.items
        return None


class WadlOperationAPI:
    "Namespace for WADL functions that operate on named operations."

    def __init__(self, operation):
        "Initialize with an operation."
        self.operation = operation

    def http_method(self):
        "The HTTP method used to invoke this operation."
        if IResourceGETOperation.implementedBy(self.operation):
            return "GET"
        elif IResourcePOSTOperation.implementedBy(self.operation):
            return "POST"
        else:
            raise AssertionError("Named operations must use GET or POST.")
