# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Classes for a resource that implements a binary file repository."""

__metaclass__ = type
__all__ = [
    'ByteStorageMarshaller',
    'ByteStorageResource',
]

from zope.interface import implements
from zope.publisher.interfaces import NotFound
from zope.schema import ValidationError

from canonical.launchpad.webapp import canonical_url

from canonical.lazr.interfaces import IByteStorageResource
from canonical.lazr.rest.resource import HTTPResource
from canonical.lazr.rest.schema import SimpleFieldMarshaller


class ByteStorageResource(HTTPResource):
    """A resource providing read-write access to a stored byte stream."""
    implements(IByteStorageResource)

    def __call__(self):
        """Handle a GET, PUT, or DELETE request."""
        if self.request.method == "GET":
            return self.do_GET()
        elif self.request.method == "PUT":
            type = self.request.headers['Content-Type']
            representation = self.request.bodyStream.getCacheStream().read()
            return self.do_PUT(type, representation)
        elif self.request.method == "DELETE":
            return self.do_DELETE()
        else:
            allow_string = "GET PUT DELETE"
            self.request.response.setStatus(405)
            self.request.response.setHeader("Allow", allow_string)

    def do_GET(self):
        if not self.context.is_stored:
            # No stored document exists here yet.
            raise NotFound(self.context, self.context.filename, self.request)
        self.request.response.setStatus(303) # See Other
        self.request.response.setHeader('Location', self.context.alias_url)
        return ''

    def do_PUT(self, type, representation):
        try:
            self.context.field.validate(representation)
        except ValidationError, e:
            self.request.response.setStatus(400) # Bad Request
            return str(e)
        self.context.createStored(type, representation)
        return ''

    def do_DELETE(self):
        self.context.deleteStored()
        return ''


class ByteStorageMarshaller(SimpleFieldMarshaller):

    def representationName(self, field_name):
        return field_name + '_link'

    def unmarshall(self, entry, field_name, bytestorage):
        """Marshall as a link to the byte storage resource."""
        return "%s/%s" % (canonical_url(entry.context), field_name)

