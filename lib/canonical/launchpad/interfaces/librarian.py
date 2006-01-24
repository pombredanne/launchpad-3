# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Librarian interfaces."""

__metaclass__ = type

__all__ = [
    'ILibraryFileAlias',
    'ILibraryFileContent',
    'ILibraryFileAliasSet',
    'NEVER_EXPIRES',
    ]

from datetime import datetime
from pytz import utc

from zope.i18nmessageid import MessageIDFactory
from zope.interface import Interface, Attribute
from zope.schema import Datetime, Int, TextLine, Bool

_ = MessageIDFactory('launchpad')

# Set the expires attribute to this constant to flag a file that
# should never be removed from the Librarian.
NEVER_EXPIRES = datetime(2038, 1, 1, 0, 0, 0, tzinfo=utc)

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
    last_accessed = Datetime(
            title=_('Date last accessed'), required=False, readonly=True
            )
    expires = Datetime(
            title=_('Expiry time'), required=False, readonly=True,
            description=_('''
                When file can be removed. Set to None if the file 
                should only be removed when it is no longer referenced
                in the database. Set it to NEVER_EXPIRES to keep it in
                the Librarian permanently.
                ''')
            )

    url = Attribute(_("The URL to this file"))

    def open():
        """Open this file for reading."""

    def read(chunksize=None):
        """Read up to `chunksize` bytes from the file.

        `chunksize` defaults to the entire file.
        """

    def chunks(chunksize=256*1024):
        """Return an iterator which reads chunks of the given file."""

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
    deleted = Bool(
            title=_('Deleted'), required=True, readonly=True
            )

class ILibraryFileAliasSet(Interface):
    def create(name, size, file, contentType, expires=None):
        """Create a file in the Librarian, returning the new ILibraryFileAlias.

        An expiry time of None means the file will never expire until it
        is no longer referenced. An expiry of NEVER_EXPIRES means a
        file that will stay in the Librarian for ever. Setting it to another
        timestamp means that the file will expire and possibly be removed
        from the Librarian at this time. See LibrarianGarbageCollection.
        """

    def __getitem__(self, key):
        """Lookup an ILibraryFileAlias by id."""
