# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Base classes for HTTP resources."""

__metaclass__ = type
__all__ = [
    'ByteStorage',
    'ByteStorageResource',
    'IByteStorage',
    'IByteStorageResource'
]

from zope.interface import Attribute, Interface, implements
from canonical.lazr.interfaces import IHTTPResource
from canonical.lazr.rest.resource import HTTPResource

class IByteStorage(Interface):
    """A sequence of bytes stored on the server."""

    bytes = Attribute("The byte sequence")


class ByteStorage:
    """See IByteStorage."""
    implements(IByteStorage)
    def __init__(self, entry, library_file):
        self.entry = entry
        self.library_file = library_file


class IByteStorageResource(IHTTPResource):
    """A resource that represents an individual object."""

    def do_GET():
        """Retrieve the bytestream.

        :return: A string representation. The outgoing
        Content-Type header should be set appropriately.
        """

    def do_PUT(media_type, representation):
        """Update the stored bytestream.

        :param media_type: The media type of the proposed new bytesteram.
        :param representation: The proposed new bytesteram.
        :return: None or an error message describing validation errors. The
            HTTP status code should be set appropriately.
        """

    def do_DELETE():
        """Delete the stored bytestream."""


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
        # If the bytestorage is just a dummy, return 404
        # Otherwise, look up the object in the library
        # Return its value
        pass

    def do_PUT(self):
        import pdb; pdb.set_trace()
        # Look up the object in the library
        # Set its value
        pass

    def do_DELETE(self):
        # Look up the object in the library
        # Delete it
        pass
