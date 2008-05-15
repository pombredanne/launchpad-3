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
        """Initialize as the backing storage for one entry's field."""
        self.entry = entry
        self.field = field
        self.file_alias = getattr(self.entry, self.filename)

    @property
    def alias_url(self):
        """See IByteStorage."""
        return self.file_alias.getURL()

    @property
    def filename(self):
        """See IByteStorage."""
        return self.field.__name__

    @property
    def is_stored(self):
        """See IByteStorage."""
        return self.file_alias is not None

    def createStored(self, type, representation):
        """See IByteStorage."""
        stored = getUtility(ILibraryFileAliasSet).create(
            name=self.filename, size=len(representation),
            file=StringIO(representation), contentType=type)
        setattr(self.entry, self.filename, stored)

    def deleteStored(self):
        """See IByteStorage."""
        setattr(self.entry, self.filename, None)
