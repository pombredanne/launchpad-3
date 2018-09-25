# Copyright 2011-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Launchpad-specific field marshallers for the web service."""

__metaclass__ = type

__all__ = [
    'TextFieldMarshaller',
    ]


from lazr.restful.interfaces import (
    IEntry,
    IFieldMarshaller,
    )
from lazr.restful.marshallers import (
    SimpleFieldMarshaller,
    TextFieldMarshaller as LazrTextFieldMarshaller,
    )
from zope.component import (
    getMultiAdapter,
    getUtility,
    )
from zope.component.interfaces import ComponentLookupError
from zope.schema.interfaces import (
    IField,
    RequiredMissing,
    )

from lp.services.utils import obfuscate_email
from lp.services.webapp.interfaces import ILaunchBag


class TextFieldMarshaller(LazrTextFieldMarshaller):
    """Do not expose email addresses for anonymous users."""

    def unmarshall(self, entry, value):
        """See `IFieldMarshaller`.

        Return the value as is.
        """

        if (value is not None and getUtility(ILaunchBag).user is None):
            return obfuscate_email(value)
        return value


class InlineObjectFieldMarshaller(SimpleFieldMarshaller):
    """A marshaller that represents an object as a dict.

    lazr.restful represents objects as URL references by default, but that
    isn't what we want in all cases.

    To use this marshaller to read JSON input data, you must register an
    adapter from the expected top-level type of the loaded JSON data
    (usually `dict`) to the `InlineObject` field's schema.  The adapter will
    be called with the deserialised input data, with all inner fields
    already converted as indicated by the schema.
    """

    def unmarshall(self, entry, value):
        """See `IFieldMarshaller`."""
        result = {}
        for name in self.field.schema.names(all=True):
            field = self.field.schema[name]
            if IField.providedBy(field):
                marshaller = getMultiAdapter(
                    (field, self.request), IFieldMarshaller)
                sub_value = getattr(value, name, field.default)
                try:
                    sub_entry = getMultiAdapter(
                        (sub_value, self.request), IEntry)
                except ComponentLookupError:
                    sub_entry = entry
                result[name] = marshaller.unmarshall(sub_entry, sub_value)
        return result

    def _marshall_from_json_data(self, value):
        """See `SimpleFieldMarshaller`."""
        template = {}
        for name in self.field.schema.names(all=True):
            field = self.field.schema[name]
            if IField.providedBy(field):
                if field.required and name not in value:
                    raise RequiredMissing(name)
                if name in value:
                    marshaller = getMultiAdapter(
                        (field, self.request), IFieldMarshaller)
                    template[name] = marshaller.marshall_from_json_data(
                        value[name])
        return self.field.schema(template)
