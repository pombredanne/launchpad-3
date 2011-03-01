# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Database access layer for the Librarian."""

__metaclass__ = type
__all__ = [
    'Library',
    'read_transaction',
    'write_transaction',
    ]

from sqlobject.sqlbuilder import AND
from storm.expr import SQL

from canonical.database.sqlbase import (
    session_store,
    )
from canonical.launchpad.database.librarian import (
    LibraryFileAlias,
    LibraryFileContent,
    TimeLimitedToken,
    )



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
        return [fc.id for fc in LibraryFileContent.selectBy(sha1=digest)]

    def getAlias(self, aliasid, token, path):
        """Returns a LibraryFileAlias, or raises LookupError.

        A LookupError is raised if no record with the given ID exists
        or if not related LibraryFileContent exists.

        :param token: The token for the file. If None no token is present.
            When a token is supplied, it is looked up with path.
        :param path: The path the request is for, unused unless a token
            is supplied; when supplied it must match the token. The 
            value of path is expected to be that from a twisted request.args
            e.g. /foo/bar. 
        """
        restricted = self.restricted
        if token and path:
            # with a token and a path we may be able to serve restricted files
            # on the public port.
            store = session_store()
            token_found = store.find(TimeLimitedToken,
                SQL("age(created) < interval '1 day'"),
                TimeLimitedToken.token==token,
                TimeLimitedToken.path==path).is_empty()
            store.reset()
            if token_found:
                raise LookupError("Token stale/pruned/path mismatch")
            else:
                restricted = True
        alias = LibraryFileAlias.selectOne(AND(
            LibraryFileAlias.q.id==aliasid,
            LibraryFileAlias.q.contentID==LibraryFileContent.q.id,
            LibraryFileAlias.q.restricted==restricted,
            ))
        if alias is None:
            raise LookupError("No file alias with LibraryFileContent")
        return alias

    def getAliases(self, fileid):
        results = LibraryFileAlias.select(AND(
                LibraryFileAlias.q.contentID==LibraryFileContent.q.id,
                LibraryFileContent.q.id==fileid,
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

