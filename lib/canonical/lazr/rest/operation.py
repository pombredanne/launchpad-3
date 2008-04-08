# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Base classes for one-off HTTP operations."""

from zope.app.form.interfaces import InputErrors
from zope.formlib.form import Fields, setUpWidgets
from zope.interface import implements

from canonical.lazr.interfaces import (
    IResourceGETOperation, IResourcePOSTOperation)

__metaclass__ = type
__all__ = [
    'ResourceGETOperation',
    'ResourcePOSTOperation'
]

class ResourceOperation:
    """A one-off operation associated with a resource."""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        values, errors = self.validate()
        if len(errors) == 0:
            return self.call(**values)
        else:
            self.request.response.setStatus(400)
            self.request.response.setHeader('Content-type', 'text/plain')
            return "\n".join(errors)

    def validate(self):
        """Validate incoming arguments against the operation schema.

        :return: A tuple (values, errors). 'values' is a dictionary of
        validated, preprocessed values to be used as parameters when
        invoking the operation. 'errors' is a list of validation errors.
        """
        validated_values = {}

        # Obtain field objects for the operation's parameters.
        fields = Fields(*self.params)

        # Data came in the HTTP request as 'fieldname=value', but Zope
        # expects all field names to have some prefix and then a dot,
        # eg. 'op.fieldname=value'. So we create a fake request form.
        # This code can be removed when we upgrade Zope.
        old_form = self.request.form
        new_form = dict([("op." + key, value)
                         for (key, value) in self.request.form.items()])
        self.request.form = new_form

        # Convert the field objects into widgets. Widgets know how to
        # take incoming string key-value pairs from an HTTP request
        # and transform them into objects that will pass field
        # validation, and that will be useful when the operation is
        # invoked.
        try:
            widgets = setUpWidgets(fields, 'op', self, self.request)
            errors = []
            for widget in widgets:
                # When talking about a field outside this method,
                # strip the prefix we had to add to the widget name.
                field_name = widget.name[widget.name.find('.')+1:]
                if widget.hasValidInput():
                    validated_values[field_name] = widget.getInputValue()
                else:
                    errors.append("%s: %s" % (field_name, widget.error()))
        finally:
            # Restore the old form in case someone else needs it.
            self.request.form = old_form

        return (validated_values, errors)

    def call(self, **kwargs):
        """Actually invoke the operation."""
        raise NotImplementedError


class ResourceGETOperation(ResourceOperation):
    """See `IResourceGETOperation`."""
    implements(IResourceGETOperation)


class ResourcePOSTOperation(ResourceOperation):
    """See `IResourcePOSTOperation`."""
    implements(IResourcePOSTOperation)

