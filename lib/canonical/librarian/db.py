# Copyright 2004 Canonical Ltd.  All rights reserved.

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

    def getAlias(self, fileid, filename):
        """Returns a LibraryFileAlias, or raises LookupError."""
        alias = LibraryFileAlias.selectOneBy(
            contentID=fileid, filename=filename)
        if alias is None:
            raise LookupError('Alias %s: %r' % (fileid, filename))
        return alias

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
        try:
            existing = self.getAlias(fileid, filename)
            if existing.mimetype == mimetype:
                return existing.id
        except LookupError:
            pass

        return LibraryFileAlias(contentID=fileid, filename=filename,
                                mimetype=mimetype).id

