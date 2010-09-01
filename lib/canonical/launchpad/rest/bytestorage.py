# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Base classes for HTTP resources."""

__metaclass__ = type
__all__ = [
    'LibraryBackedByteStorage',
    'RestrictedLibraryBackedByteStorage',
]


from cStringIO import StringIO

from lazr.restful.interfaces import IByteStorage
from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.browser.librarian import ProxiedLibraryFileAlias
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData


class LibraryBackedByteStorage:
    """See `IByteStorage`."""
    implements(IByteStorage, ICanonicalUrlData)

    def __init__(self, entry, field):
        """Initialize as the backing storage for one entry's field."""
        self.entry = entry
        self.field = field
        self.file_alias = getattr(self.entry, self.field.__name__)

    @property
    def rootsite(self):
        """See `ICanonicalUrlData`"""
        return None

    @property
    def inside(self):
        """See `ICanonicalUrlData`"""
        return self.entry.context

    @property
    def path(self):
        """See `ICanonicalUrlData`"""
        return self.field.__name__

    @property
    def alias_url(self):
        """See `IByteStorage`."""
        return self.file_alias.getURL()

    @property
    def filename(self):
        """See `IByteStorage`."""
        if self.is_stored:
            return self.file_alias.filename
        return self.field.__name__

    @property
    def is_stored(self):
        """See `IByteStorage`."""
        return self.file_alias is not None

    def createStored(self, mediaType, representation, filename=None):
        """See `IByteStorage`."""
        if filename is None:
            filename = self.filename
        stored = getUtility(ILibraryFileAliasSet).create(
            name=filename, size=len(representation),
            file=StringIO(representation), contentType=mediaType)
        setattr(self.entry, self.field.__name__, stored)

    def deleteStored(self):
        """See `IByteStorage`."""
        setattr(self.entry, self.field.__name__, None)


class RestrictedLibraryBackedByteStorage(LibraryBackedByteStorage):
    """See `IByteStorage`.

    This variant of LibraryBackedByteStorage provides an alias_url
    which points to a StreamOrRedirectLibraryFileAliasView for
    restricted Librarian files.
    """

    @property
    def alias_url(self):
        """See `IByteStorage`."""
        return ProxiedLibraryFileAlias(
            self.file_alias, self.entry.context).api_url
