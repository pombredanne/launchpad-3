# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Librarian interfaces."""

__metaclass__ = type

__all__ = [
    'ILibraryFileAlias',
    'ILibraryFileContent',
    'ILibraryFileAliasSet',
    ]

from zope.i18nmessageid import MessageIDFactory
from zope.interface import Interface, Attribute
from zope.schema import Datetime, Int, TextLine

_ = MessageIDFactory('launchpad')

class ILibraryFileAlias(Interface):
    id = Int(
            title=_('Library File Alias ID'), required=True, readonly=True,
            )
    content = Attribute('Library file content')
    filename = TextLine(
            title=_('Filename'), required=True, readonly=True
            )
    mimetype = TextLine(
            title=_('MIME type'), required=True, readonly=True
            )

    url = Attribute(_("The URL to this file"))

    def open():
        """Open this file for reading."""

    def read(chunksize=None):
        """Read up to `chunksize` bytes from the file.

        `chunksize` defaults to the entire file.
        """

    def close():
        """Close this file."""


class ILibraryFileContent(Interface):
    """Actual data in the Librarian.

    This should not be used outside of the librarian internals.
    """
    id = Int(
            title=_('Library File Content ID'), required=True, readonly=True,
            )
    datecreated = Datetime(
            title=_('Date created'), required=True, readonly=True
            )
    datemirrored = Datetime(
            title=_('Date mirrored'), required=True, readonly=True
            )
    filesize = Int(
            title=_('File size'), required=True, readonly=True
            )
    sha1 = TextLine(
            title=_('SHA-1 hash'), required=True, readonly=True
            )

class ILibraryFileAliasSet(Interface):
    def create(name, size, file, contentType):
        """Create a file in the Librarian, returning the new ILibraryFileAlias.
        """

    def __getitem__(self, key):
        """Lookup an ILibraryFileAlias by id."""
