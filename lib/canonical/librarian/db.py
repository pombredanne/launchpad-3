# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.database import LibraryFileContent, LibraryFileAlias

from sqlobject import IntCol, StringCol, DateTimeCol, ForeignKey
from sqlobject import SQLObjectNotFound


class Library:

    # The following methods are read-only queries.

    def lookupBySHA1(self, digest):
        return [fc.id for fc in 
                LibraryFileContent.selectBy(sha1=digest)]

    def getAlias(self, aliasid):
        """Returns a LibraryFileAlias, or raises LookupError."""
        try:
            return LibraryFileAlias.get(aliasid)
        except SQLObjectNotFound:
            raise LookupError(aliasid)

    def getAliases(self, fileid):
        results = LibraryFileAlias.selectBy(contentID=fileid)
        return [(a.id, a.filename, a.mimetype) for a in results]

    def getByAlias(self, aliasid):
        return LibraryFileAlias.get(aliasid)

    def hasContent(self, contentID):
        # XXX: write test.
        try:
            LibraryFileContent.get(contentID)
        except SQLObjectNotFound:
            return False
        else:
            return True

    # the following methods are used for adding to the library

    def add(self, digest, size):
        lfc = LibraryFileContent(filesize=size, sha1=digest)
        return lfc.id

    def addAlias(self, fileid, filename, mimetype):
        """Add an alias, and return its ID.

        If a matching alias already exists, it will return that ID instead.
        """
        return LibraryFileAlias(contentID=fileid, filename=filename,
                                mimetype=mimetype).id

