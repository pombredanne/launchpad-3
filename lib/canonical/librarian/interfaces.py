# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.interface import Interface

class IFileUploadClient(Interface):
    def addFile(name, size, file):
        """Add a file to the librarian.

        :param name: Name to store the file as
        :param size: Size of the file
        :param file: File-like object with the content in it

        :raises UploadFailed: If the server rejects the upload for some reason
        """

class IFileDownloadClient(Interface):
    def getURLForAlias(aliasID):
        """Returns the URL to the given file"""

    def getFileByAlias(aliasID):
        """Returns a file-like object to read the file contents from"""

class ILibrarianClient(IFileUploadClient, IFileDownloadClient):
    pass

