# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Base classes for one-off HTTP operations."""

import simplejson
import types

from zope.component import getMultiAdapter, queryAdapter
from zope.interface import implements
from zope.schema.interfaces import RequiredMissing, ValidationError

from canonical.lazr.interfaces import (
    ICollection, IEntry, IFieldMarshaller, IResourceGETOperation,
    IResourcePOSTOperation)
from canonical.lazr.rest.resource import (
    BatchingResourceMixin, EntryResource, ResourceJSONEncoder)

__metaclass__ = type
__all__ = [
    'ResourceOperation',
    'ResourceGETOperation',
    'ResourcePOSTOperation'
]


class ResourceOperation(BatchingResourceMixin):
    """A one-off operation associated with a resource."""

    JSON_TYPE = 'application/json'

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        values, errors = self.validate()
        if len(errors) == 0:
            return self.processResult(self.call(**values))
        else:
            self.request.response.setStatus(400)
            self.request.response.setHeader('Content-type', 'text/plain')
            return "\n".join(errors)

    def processResult(self, result):
        """Process the result of a custom operation."""
        if (self.request.response.getHeader('Content-Type') is not None
            or self.request.response.getStatus() != 599):
            # The operation took care of everything and just needs
            # this object served to the client.
            return result

        basic_types = (basestring, bool, int, float, types.NoneType,
                       types.TupleType, types.ListType, types.DictionaryType)
        if not isinstance(result, basic_types):
            try:
                iterator = iter(result)
                # Since that didn't throw an exception, we have a collection
                # or a list of something.
                self.request.response.setHeader('Content-Type', self.JSON_TYPE)
                return self.batch(result, self.request)
            except TypeError:
                pass

            if queryAdapter(result, IEntry):
                # We have an individual entry. Dump it to JSON.
                result = EntryResource(result, self.request)
            else:
                # The result can't be serialized to JSON.
                raise ValueError(
                    "Operation result (%s) can't be serialized to JSON"
                    % result)

        json_representation = simplejson.dumps(
            result, cls=ResourceJSONEncoder)
        self.request.response.setStatus(200)
        self.request.response.setHeader('Content-Type', self.JSON_TYPE)
        return json_representation

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
        missing = object()
        for field in self.params:
            name = field.__name__
            if (self.request.get(name, missing) is missing
                and not field.required):
                value = field.default
            else:
                marshaller = getMultiAdapter(
                    (field, self.request), IFieldMarshaller)
                try:
                    value = marshaller.marshall_from_request(
                        self.request.form.get(name))
                except ValueError, e:
                    errors.append("%s: %s" % (name, e))
                    continue
            field = field.bind(self.context)
            try:
                field.validate(value)
            except RequiredMissing:
                errors.append("%s: Required input is missing." % name)
            except ValidationError, e:
                errors.append("%s: %s" % (name, e))
            else:
                validated_values[name] = value
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

