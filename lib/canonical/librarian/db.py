# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

"""Database access layer for the Librarian."""

__metaclass__ = type
__all__ = [
    'Library',
    ]

from canonical.launchpad.database import LibraryFileContent, LibraryFileAlias

from sqlobject.sqlbuilder import AND


class Library:
    """Class that encapsulates the database interface for the librarian."""

    def __init__(self, restricted=False):
        """Create a new database access object.

        :param restricted: If this is set to true, only restricted
            will be served. Otherwise only public files will be served.
            Files created in this library will marked as restricted.
        """
        self.restricted = restricted

    # The following methods are read-only queries.

    def lookupBySHA1(self, digest):
        return [fc.id for fc in
                LibraryFileContent.selectBy(sha1=digest, deleted=False)]

    def getAlias(self, aliasid):
        """Returns a LibraryFileAlias, or raises LookupError."""
        alias = LibraryFileAlias.selectOne(AND(
            LibraryFileAlias.q.id==aliasid,
            LibraryFileContent.q.deleted==False,
            LibraryFileAlias.q.contentID==LibraryFileContent.q.id,
            LibraryFileAlias.q.restricted==self.restricted,
            ))
        if alias is None:
            raise LookupError
        return alias

    def getAliases(self, fileid):
        results = LibraryFileAlias.select(AND(
                LibraryFileAlias.q.contentID==LibraryFileContent.q.id,
                LibraryFileContent.q.id==fileid,
                LibraryFileContent.q.deleted==False,
                LibraryFileAlias.q.restricted==self.restricted,
                ))
        return [(a.id, a.filename, a.mimetype) for a in results]

    # the following methods are used for adding to the library

    def add(self, digest, size, md5Digest):
        lfc = LibraryFileContent(filesize=size, sha1=digest, md5=md5Digest)
        return lfc.id

    def addAlias(self, fileid, filename, mimetype, expires=None):
        """Add an alias, and return its ID.

        If a matching alias already exists, it will return that ID instead.
        """
        return LibraryFileAlias(contentID=fileid, filename=filename,
                                mimetype=mimetype, expires=expires,
                                restricted=self.restricted).id

