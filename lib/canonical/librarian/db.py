# Copyright 2004 Canonical Ltd.  All rights reserved.
#

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.database import LibraryFileContent, LibraryFileAlias

from sqlobject import IntCol, StringCol, DateTimeCol, ForeignKey

class AliasConflict(Exception):
    pass

class Library(object):
    def lookupBySHA1(self, digest):
        return [fc.id for fc in LibraryFileContent.selectBy(sha1=digest)]

    def add(self, digest, size):
        txn = LibraryFileContent._connection.transaction()
        lfc = LibraryFileContent(filesize=size, sha1=digest, connection=txn)
        return lfc.id, txn

    def addAlias(self, fileid, filename, mimetype, txn=None):
        try:
            existing = self.getAlias(fileid, filename)
            if existing.mimetype != mimetype:
                # FIXME: The DB should probably have a constraint that enforces
                # this i.e. UNIQUE(content, filename)
                raise AliasConflict
            return existing.id
        except IndexError:
            if txn is not None:
                return LibraryFileAlias(contentID=fileid, filename=filename,
                        mimetype=mimetype, connection=txn).id
            else:
                return LibraryFileAlias(contentID=fileid, filename=filename,
                        mimetype=mimetype).id

    def getAlias(self, fileid, filename, connection=None):
        return LibraryFileAlias.selectBy(contentID=fileid, filename=filename,
                                         connection=connection)[0]

    def getAliases(self, fileid, connection=None):
        results = LibraryFileAlias.selectBy(contentID=fileid,
                                            connection=connection)
        return [(a.id, a.filename, a.mimetype) for a in results]

