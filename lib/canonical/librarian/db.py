# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import sys

import transaction

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.database import LibraryFileContent, LibraryFileAlias
from canonical.launchpad.webapp.adapter import DisconnectionError

from sqlobject import SQLObjectNotFound
from sqlobject.sqlbuilder import AND


RETRY_ATTEMPTS = 3

def retry_transaction(func):
    def wrapper(*args, **kwargs):
        attempt = 0
        while True:
            attempt += 1
            try:
                return func(*args, **kwargs)
            except DisconnectionError:
                print "*** Disconnected"
                if attempt >= RETRY_ATTEMPTS:
                    raise # tried too many times
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper

def read_transaction(func):
    def wrapper(*args, **kwargs):
        print >>sys.stderr, "*** Begin Transaction", func.__name__
        transaction.begin()
        try:
            return func(*args, **kwargs)
        finally:
            print >>sys.stderr, "*** Abort Transaction"
            transaction.abort()
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return retry_transaction(wrapper)

def write_transaction(func):
    def wrapper(*args, **kwargs):
        print >>sys.stderr, "*** Begin Transaction", func.__name__
        transaction.begin()
        try:
            ret = func(*args, **kwargs)
        except:
            print >>sys.stderr, "*** Abort Transaction"
            transaction.abort()
            raise
        print >>sys.stderr, "*** Commit Transaction"
        transaction.commit()
        return ret
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return retry_transaction(wrapper)


class Library:

    # The following methods are read-only queries.

    def lookupBySHA1(self, digest):
        return [fc.id for fc in 
                LibraryFileContent.selectBy(sha1=digest, deleted=False)]

    def getAlias(self, aliasid):
        """Returns a LibraryFileAlias, or raises LookupError."""
        alias = LibraryFileAlias.selectOne(AND(
            LibraryFileAlias.q.id==aliasid,
            LibraryFileContent.q.deleted==False,
            LibraryFileAlias.q.contentID==LibraryFileContent.q.id
            ))
        if alias is None:
            raise LookupError
        return alias

    def getAliases(self, fileid):
        results = LibraryFileAlias.select(AND(
                LibraryFileAlias.q.content==LibraryFileContent.q.id,
                LibraryFileContent.q.id==fileid,
                LibraryFileContent.q.deleted==False
                ))
        return [(a.id, a.filename, a.mimetype) for a in results]

    def getByAlias(self, aliasid):
        """XXX: Still needed? Seems to be getAlias except it might raise
        an SQLObjectNotFound instead of a LookupError -- StuartBishop 20061222
        """
        try:
            return self.getAlias(aliasid)
        except LookupError:
            raise SQLObjectNotFound(
                    "The object LibraryFileAlias by the ID %d does not exist"
                    % aliasid
                    )

    def hasContent(self, contentID):
        # XXX: write test.
        content = LibraryFileContent.selectOne(
                LibraryFileContent.q.id==contentID,
                LibraryFileContent.q.deleted==False
                )
        return content is not None

    # the following methods are used for adding to the library

    def add(self, digest, size, md5Digest):
        lfc = LibraryFileContent(filesize=size, sha1=digest, md5=md5Digest)
        return lfc.id

    def addAlias(self, fileid, filename, mimetype, expires=None):
        """Add an alias, and return its ID.

        If a matching alias already exists, it will return that ID instead.
        """
        return LibraryFileAlias(contentID=fileid, filename=filename,
                                mimetype=mimetype, expires=expires).id

