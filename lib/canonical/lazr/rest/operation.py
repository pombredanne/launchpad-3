# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Base classes for one-off HTTP operations."""

from zope.schema.interfaces import (
    ConstraintNotSatisfied, RequiredMissing, ValidationError)
from zope.component import getMultiAdapter
from zope.interface import implements

from canonical.lazr.interfaces import (
    IFieldDeserializer, IResourceGETOperation, IResourcePOSTOperation)

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
        errors = []

        # Take incoming string key-value pairs from the HTTP request.
        # Transform them into objects that will pass field validation,
        # and that will be useful when the operation is invoked.
        for field in self.params:
            name = field.__name__
            deserializer = getMultiAdapter((field, self.request),
                                           IFieldDeserializer)
            field.bind(self.context)
            try:
                value = deserializer.deserialize(self.request.get(name))
                field.validate(value)
                validated_values[name] = value
            except RequiredMissing:
                errors.append("%s: Required input is missing." % name)
            except ConstraintNotSatisfied, e:
                # This is a pretty useless error because the client
                # doesn't know which constraint wasn't satisfied.
                errors.append("%s: Constraint not satisfied: %s." % (name,
                                                                     str(e)))
            except (ValueError, ValidationError), e:
                errors.append("%s: %s" % (name, str(e)))

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

