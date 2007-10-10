# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

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

from zope.interface import Interface, Attribute
from zope.schema import Datetime, Int, TextLine, Bool

from canonical.launchpad import _

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

    # XXX Guilherme Salgado, 2007-01-18 bug=80487:
    # We can't use TextLine here because they return
    # byte strings.
    http_url = Attribute(_("The http URL to this file"))
    https_url = Attribute(_("The https URL to this file"))

    def getURL():
        """Return this file's http or https URL.

        The generated URL will be https if the use_https config variable is
        set, in order to prevent warnings about insecure objects from
        happening in some browsers.

        If config.launchpad.virtual_host.use_https is set, then return the
        https URL. Otherwise return the http URL.
        """

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
    md5 = TextLine(
            title=_('MD5 hash'), required=True, readonly=True
            )
    deleted = Bool(
            title=_('Deleted'), required=True, readonly=True
            )

class ILibraryFileAliasSet(Interface):
    def create(name, size, file, contentType, expires=None, debugID=None):
        """Create a file in the Librarian, returning the new ILibraryFileAlias.

        An expiry time of None means the file will never expire until it
        is no longer referenced. An expiry of NEVER_EXPIRES means a
        file that will stay in the Librarian for ever. Setting it to another
        timestamp means that the file will expire and possibly be removed
        from the Librarian at this time. See LibrarianGarbageCollection.
        """

    def __getitem__(key):
        """Lookup an ILibraryFileAlias by id."""

    def findBySHA1(sha1):
        """Return all LibraryFileAlias whose content's sha1 match the given
        sha1.
        """
