# Copyright 2004 Canonical Ltd.  All rights reserved.
#

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.database import LibraryFileContent, LibraryFileAlias

from sqlobject import IntCol, StringCol, DateTimeCol, ForeignKey

class AliasConflict(Exception):
    pass

class Library(object):

    # the following methods are read-only queries

    def lookupBySHA1(self, digest):
        return [fc.id for fc in 
                LibraryFileContent.selectBy(sha1=digest)]

    def getAlias(self, fileid, filename):
        return LibraryFileAlias.selectBy(contentID=fileid, filename=filename)[0]

    def getAliases(self, fileid):
        results = LibraryFileAlias.selectBy(contentID=fileid)
        return [(a.id, a.filename, a.mimetype) for a in results]

    def getByAlias(self, aliasid):
        return LibraryFileAlias.get(aliasid)

    # the following methods are used for adding to the library

    def add(self, digest, size):
        lfc = LibraryFileContent(filesize=size, sha1=digest)
        return lfc.id

    def addAlias(self, fileid, filename, mimetype):
        try:
            existing = self.getAlias(fileid, filename)
            if existing.mimetype != mimetype:
                # FIXME: The DB should probably have a constraint that enforces
                # this i.e. UNIQUE(content, filename)
                raise AliasConflict
            return existing.id
        except IndexError:
            return LibraryFileAlias(contentID=fileid, filename=filename,
                                    mimetype=mimetype).id
            
