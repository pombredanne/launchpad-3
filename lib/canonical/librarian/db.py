# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Database access layer for the Librarian."""

__metaclass__ = type
__all__ = [
    'Library',
    'read_transaction',
    'write_transaction',
    ]

from psycopg2.extensions import TransactionRollbackError
from sqlobject.sqlbuilder import AND
from storm.exceptions import DisconnectionError, IntegrityError
import transaction
from twisted.python.util import mergeFunctionMetadata

from canonical.database.sqlbase import reset_store
from canonical.launchpad.database.librarian import (
    LibraryFileContent, LibraryFileAlias)


RETRY_ATTEMPTS = 3


def retry_transaction(func):
    """Decorator used to retry database transaction failures.

    The function being decorated should not have side effects outside
    of the transaction.
    """
    def retry_transaction_decorator(*args, **kwargs):
        attempt = 0
        while True:
            attempt += 1
            try:
                return func(*args, **kwargs)
            except (DisconnectionError, IntegrityError,
                    TransactionRollbackError), exc:
                if attempt >= RETRY_ATTEMPTS:
                    raise # tried too many times
    return mergeFunctionMetadata(func, retry_transaction_decorator)


def read_transaction(func):
    """Decorator used to run the function inside a read only transaction.

    The transaction will be aborted on successful completion of the
    function.  The transaction will be retried if appropriate.
    """
    @reset_store
    def read_transaction_decorator(*args, **kwargs):
        transaction.begin()
        try:
            return func(*args, **kwargs)
        finally:
            transaction.abort()
    return retry_transaction(mergeFunctionMetadata(
        func, read_transaction_decorator))


def write_transaction(func):
    """Decorator used to run the function inside a write transaction.

    The transaction will be committed on successful completion of the
    function, and aborted on failure.  The transaction will be retried
    if appropriate.
    """
    @reset_store
    def write_transaction_decorator(*args, **kwargs):
        transaction.begin()
        try:
            ret = func(*args, **kwargs)
        except:
            transaction.abort()
            raise
        transaction.commit()
        return ret
    return retry_transaction(mergeFunctionMetadata(
        func, write_transaction_decorator))


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

    def getAlias(self, aliasid):
        """Returns a LibraryFileAlias, or raises LookupError.

        A LookupError is raised if no record with the given ID exists
        or if not related LibraryFileContent exists.
        """
        alias = LibraryFileAlias.selectOne(AND(
            LibraryFileAlias.q.id==aliasid,
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

