# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
# PyLint doesn't grok Zope interfaces.
# pylint: disable-msg=E0213
__metaclass__ = type

from zope.interface import Interface


class LibrarianFailure(Exception):
    """Base class for failures trying to use the libararian."""


class UploadFailed(LibrarianFailure):
    pass


class DownloadFailed(LibrarianFailure):
    pass


class LibrarianServerError(Exception):
    """An error indicating that the Librarian server is not responding."""


# the default time in seconds FileUploadClient.getByFileAlias() will
# retry to open a connection to the Librarain server before raising
# LibrarianServerError.
LIBRARIAN_SERVER_TIMEOUT = 5

class IFileUploadClient(Interface):
    def addFile(name, size, file, contentType, expires=None):
        """Add a file to the librarian.

        :param name: Name to store the file as
        :param size: Size of the file
        :param file: File-like object with the content in it
        :param expires: Expiry time of file, or None to keep until unreferenced

        :raises UploadFailed: If the server rejects the upload for some reason

        Database insertions are done by the client, so access to the
        LibraryFileAlias and LibraryFileContent objects is available
        immediately. However, the newly uploaded file cannot be retrieved
        from the Librarian until the client transaction has been committed.

        Returns the id of the newly added LibraryFileAlias
        """

    def remoteAddFile(name, size, file, contentType, expires=None):
        """Add a file to the librarian using the remote protocol.

        As per addFile, except that the database insertions are done by the
        librarian. This means that the corresponding rows in the
        LibraryFileAlias and LibraryFileContent tables will not be available
        until the client transaction has been committed. However, the data
        is retrievable from the Librarian even if the client transaction rolls
        back.

        This method is used to ensure files get placed into the Librarian even
        when the current transaction may be rolled back (eg. for storing
        exception information in the Librarian), or when the client does not
        have a database connection (eg. untrusted code).

        Returns the URL of the newly added file.
        """


class IFileDownloadClient(Interface):
    def getURLForAlias(aliasID):
        """Returns the URL to the given file"""

    def getFileByAlias(aliasID, timeout=LIBRARIAN_SERVER_TIMEOUT):
        """Returns a file-like object to read the file contents from.

        :param aliasID: The alias ID identifying the file.
        :param timeout: The number of seconds the method retries to open
            a connection to the Librarian server. If the connection
            cannot be established in the given time, a
            LibrarianServerError is raised.
        :return: A file-like object to read the file contents from.
        :raises DownloadFailed: If the alias is not found.
        :raises LibrarianServerError: If the librarain server is
            unreachable or returns an 5xx HTTPError.
        """


class ILibrarianClient(IFileUploadClient, IFileDownloadClient):
    """Interface for the librarian client."""


class IRestrictedLibrarianClient(ILibrarianClient):
    """A version of the client that connects to a restricted librarian."""

