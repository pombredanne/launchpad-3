# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Base classes for one-off HTTP operations."""

import simplejson
import types

from zope.component import getMultiAdapter, queryAdapter
from zope.interface import Attribute, implements
from zope.interface.interfaces import IInterface
from zope.schema import Field
from zope.schema.interfaces import (
    IField, RequiredMissing, ValidationError, WrongType)
from zope.security.proxy import isinstance as zope_isinstance

from canonical.lazr.interfaces import (
    ICollection, IFieldMarshaller, IResourceGETOperation,
    IResourcePOSTOperation)
from canonical.lazr.rest.resource import (
    BatchingResourceMixin, CollectionResource, ResourceJSONEncoder)

__metaclass__ = type
__all__ = [
    'IObjectLink',
    'ObjectLink',
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
            return self.encodeResult(self.call(**values))
        else:
            self.request.response.setStatus(400)
            self.request.response.setHeader('Content-type', 'text/plain')
            return "\n".join(errors)

    def encodeResult(self, result):
        """Encode the result of a custom operation into a string.

        This method is responsible for turning the return value of a
        custom operation into a string that can be served . It's also
        responsible for setting the Content-Type header and the status
        code.
        """
        if (self.request.response.getHeader('Content-Type') is not None
            or self.request.response.getStatus() != 599):
            # The operation took care of everything and just needs
            # this object served to the client.
            return result

        if queryAdapter(result, ICollection):
            # If the result is a web service collection, serve only one
            # batch of the collection.
            result = CollectionResource(
                ICollection(result), self.request).batch()
        elif not(zope_isinstance(result,
                                 (basestring, set, types.TupleType,
                                  types.ListType, types.DictionaryType))):
            # If the result provides an iterator but isn't a list or
            # string, it's an object capable of batching a large
            # dataset. Serve only one batch of the dataset.
            try:
                iterator = iter(result)
                # It's a list.
                result = self.batch(result, self.request)
            except TypeError:
                pass
        else:
            # The result doesn't need to be batched. Serialize the
            # whole thing to JSON.
            pass

        # Serialize the result to JSON. Any embedded entries will be
        # automatically serialized.
        try:
            json_representation = simplejson.dumps(
                result, cls=ResourceJSONEncoder)
        except TypeError:
            raise TypeError("Could not serialize object %s to JSON." %
                            result)

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


class IObjectLink(IField):
    """Field containing a link to an object."""

    schema = Attribute("schema",
        u"The Interface of the Object on the other end of the link.")

class ObjectLink(Field):
    """A reference to an object."""
    implements(IObjectLink)

    def __init__(self, schema, **kw):
        if not IInterface.providedBy(schema):
            raise WrongType

        self.schema = schema
        super(ObjectLink, self).__init__(**kw)
