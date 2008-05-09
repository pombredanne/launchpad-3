# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Base classes for HTTP resources."""

__metaclass__ = type
__all__ = [
    'ByteStorageResource',
    'IByteStorage',
    'IByteStorageResource',
    'LibraryBackedByteStorage',
]


from cStringIO import StringIO

from zope.component import getUtility
from zope.interface import Attribute, Interface, implements
from zope.publisher.interfaces import NotFound

from canonical.lazr.interfaces import IHTTPResource
from canonical.lazr.rest.resource import HTTPResource

from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet


class IByteStorage(Interface):
    """A sequence of bytes stored on the server.

    The bytestream is expected to have a URL other than the one used
    by the web service.
    """

    url = Attribute("The external URL to the byte stream.")
    filename = Attribute("Filename for the byte stream.")

    def create_stored(type, representation):
        """Create a new stored bytestream."""


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


class LibraryBackedByteStorage:
    """See IByteStorage."""
    implements(IByteStorage)

    def __init__(self, entry, field):
        """See IByteStorage."""
        self.entry = entry
        self.field = field

    @property
    def url(self):
        """See IByteStorage."""
        return self.get_stored().getURL()

    @property
    def filename(self):
        """See IByteStorage."""
        return self.field.__name__

    def create_stored(self, type, representation):
        """See IByteStorage."""
        return getUtility(ILibraryFileAliasSet).create(
            name=self.filename, size=len(representation),
            file=StringIO(representation), contentType=type)

    def _getLibraryStorage(self):
        return getattr(self.entry, self.context.filename)
