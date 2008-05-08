# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Base classes for HTTP resources."""

__metaclass__ = type
__all__ = [
    'ByteStorage',
    'ByteStorageResource',
    'IByteStorage',
    'IByteStorageResource'
]


from cStringIO import StringIO

from zope.component import getUtility
from zope.interface import Attribute, Interface, implements
from zope.publisher.interfaces import NotFound

from canonical.lazr.interfaces import IHTTPResource
from canonical.lazr.rest.resource import HTTPResource

from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet


class IByteStorage(Interface):
    """A sequence of bytes stored on the server."""

    bytes = Attribute("The byte sequence")


class ByteStorage:
    """See IByteStorage."""
    implements(IByteStorage)
    def __init__(self, entry, field):
        self.entry = entry
        self.field = field

    @property
    def filename(self):
        """Name of the file to be stored."""
        return self.field.__name__

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
        file_alias = getattr(self.context.entry, self.context.filename)
        if file_alias is None:
            raise NotFound(self.context, '', self.request)
        self.request.response.setStatus(303) # See Other
        self.request.response.setHeader('Location', file_alias.getURL())

    def do_PUT(self, type, representation):
        # Look up the object in the library
        # Set its value
        file_alias = getattr(self.context.entry, self.context.filename)
        if file_alias is None:
            # Response code should be 201
            pass
        file_alias = getUtility(ILibraryFileAliasSet).create(
            name=self.context.filename, size=len(representation),
            file=StringIO(representation), contentType=type)
        setattr(self.context.entry, self.context.filename, file_alias)

    def do_DELETE(self):
        setattr(self.context.entry, self.context.filename, None)

