# Copyright 2008 Canonical Ltd.  All rights reserved.
#
"""Implementation of the ws: namespace in TALES."""

__metaclass__ = type

from zope.schema import getFields
from zope.schema.interfaces import IObject
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp import canonical_url

from canonical.lazr.interfaces import ICollectionField


class WadlAPI:
    "Namespace for WADL functions that operate on resources."

    def __init__(self, resource):
        underlying_resource = removeSecurityProxy(resource)
        self.context = underlying_resource.context

    def url(self):
        """Return the full URL to the object."""
        return canonical_url(self.context)


class WadlEntryAPI(WadlAPI):
    "Namespace for WADL functions that operate on entry resources."

    def __init__(self, entry_resource):
        self.resource = entry_resource
        self.entry = self.resource.entry
        self.schema = self.entry.schema
        underlying_resource = removeSecurityProxy(entry_resource)
        self.data_object = underlying_resource.context

    def singular_type(self):
        "Return the singular name for this object type."
        return self.data_object.__class__.__name__

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
        return "#" + self.singular_type() + '-patch'

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
        self.field = field

    def path(self):
        name = self.field.__name__
        if ICollectionField.providedBy(self.field):
            repr_name = name + '_collection_link'
        elif IObject.providedBy(self.field):
            repr_name = name + '_link'
        else:
            repr_name = name
        return '["%s"]' % repr_name

    def is_link(self):
        return (IObject.providedBy(self.field) or
                ICollectionField.providedBy(self.field))
