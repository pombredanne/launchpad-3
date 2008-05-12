# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Classes for a resource that implements a binary file repository."""

__metaclass__ = type
__all__ = [
    'ByteStorageDeserializer',
    'ByteStorageResource',
]


from zope.interface import implements
from zope.publisher.interfaces import NotFound

from canonical.launchpad.webapp import canonical_url

from canonical.lazr.interfaces import IByteStorageResource
from canonical.lazr.rest.resource import HTTPResource
from canonical.lazr.rest.schema import SimpleFieldDeserializer


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
        file_object = getattr(self.context.entry, self.context.filename)
        if file_object is None:
            # No stored document exists here yet.
            raise NotFound(self.context, '', self.request)
        self.request.response.setStatus(303) # See Other
        self.request.response.setHeader('Location', file_object.getURL())

    def do_PUT(self, type, representation):
        file_object = self.context.create_stored(type, representation)
        setattr(self.context.entry, self.context.filename, file_object)

    def do_DELETE(self):
        setattr(self.context.entry, self.context.filename, None)


class ByteStorageDeserializer(SimpleFieldDeserializer):

    def serialize(self, name, entry, bytestorage):
        """Serialize as a link to the byte storage resource."""
        return (name + '_link', "%s/%s" % (canonical_url(entry), name))

