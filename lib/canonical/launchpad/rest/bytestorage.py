# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Base classes for HTTP resources."""

__metaclass__ = type
__all__ = [
    'LibraryBackedByteStorage',
]


from cStringIO import StringIO

from zope.component import getUtility
from zope.interface import implements

from canonical.lazr.interfaces import IByteStorage, IHTTPResource

from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet


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
