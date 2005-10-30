# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
#

__metaclass__ = type

import sha
import urllib
import urllib2
import socket
import time
from socket import SOCK_STREAM, AF_INET
from select import select
from urlparse import urljoin

from canonical.config import config
from canonical.database.sqlbase import cursor
from canonical.librarian.interfaces import UploadFailed, DownloadFailed

__all__ = ['FileUploadClient', 'FileDownloadClient', 'LibrarianClient']

class FileUploadClient:
    """Simple blocking client for uploading to the librarian."""

    def _connect(self):
        """Connect this client.
        
        The host and port default to what is specified in the configuration
        """
        host = config.librarian.upload_host
        port = config.librarian.upload_port

        try:
            self.s = socket.socket(AF_INET, SOCK_STREAM)
            self.s.connect((host, port))
            self.f = self.s.makefile('w+', 0)
        except socket.error, x:
            raise UploadFailed(str(x))

    def _close(self):
        """Close connection"""
        del self.s
        del self.f

    def _checkError(self):
        if select([self.s], [], [], 0)[0]:
            response = self.f.readline().strip()
            raise UploadFailed, 'Server said: ' + response
            
    def _sendLine(self, line):
        self.f.write(line + '\r\n')
        self._checkError()

    def _sendHeader(self, name, value):
        self._sendLine('%s: %s' % (name, value))

    def addFile(self, name, size, file, contentType, expires=None):
        """Add a file to the librarian.

        :param name: Name to store the file as
        :param size: Size of the file
        :param file: File-like object with the content in it
        :param contentType: mime-type, e.g. text/plain
        :param expires: Expiry time of file. See LibrarianGarbageCollection.
            Set to None to only expire when it is no longer referenced.

        :returns: aliasID as an integer
        
        :raises UploadFailed: If the server rejects the upload for some reason,
            or the size is 0.
        """
        if file is None:
            raise TypeError('Bad File Descriptor: %s' % repr(file))
        if size <= 0:
            raise UploadFailed('Invalid length: %d' % size)

        if isinstance(name, unicode):
            name = name.encode('utf-8')

        # Import in this method to avoid a circular import
        from canonical.launchpad.database import LibraryFileContent
        from canonical.launchpad.database import LibraryFileAlias

        self._connect()
        try:
            # Generate new content and alias IDs.
            # (we'll create rows with these IDs later, but not yet)
            cur = cursor()
            cur.execute("SELECT nextval('libraryfilecontent_id_seq')")
            contentID = cur.fetchone()[0]
            cur.execute("SELECT nextval('libraryfilealias_id_seq')")
            aliasID = cur.fetchone()[0]

            # Send command
            self._sendLine('STORE %d %s' % (size, name))

            # Send headers
            self._sendHeader('File-Content-ID', contentID)
            self._sendHeader('File-Alias-ID', aliasID)

            # Send blank line
            self._sendLine('')
            
            # Prepare to the upload the file
            digester = sha.sha()
            bytesWritten = 0

            # Read in and upload the file 64kb at a time, by using the two-arg
            # form of iter (see
            # /usr/share/doc/python2.4/html/lib/built-in-funcs.html#l2h-42).
            for chunk in iter(lambda: file.read(1024*64), ''):
                self.f.write(chunk)
                bytesWritten += len(chunk)
                digester.update(chunk)
            
            assert bytesWritten == size, (
                'size is %d, but %d were read from the file' 
                % (size, bytesWritten))
            self.f.flush()

            # Read response
            response = self.f.readline().strip()
            if response != '200':
                raise UploadFailed, 'Server said: ' + response

            # Add rows to DB
            LibraryFileContent(id=contentID, filesize=size,
                            sha1=digester.hexdigest())
            LibraryFileAlias(id=aliasID, contentID=contentID, filename=name,
                            mimetype=contentType, expires=expires)

            assert isinstance(aliasID, (int, long)), \
                    "aliasID %r not an integer" % (aliasID,)
            return aliasID
        finally:
            self._close()

    def remoteAddFile(self, name, size, file, contentType, expires=None):
        """See canonical.librarian.interfaces.ILibrarianUploadClient"""
        if file is None:
            raise TypeError('No data')
        if size <= 0:
            raise UploadFailed('No data')
        if isinstance(name, unicode):
            name = name.encode('utf-8')
        self._connect()
        try:
            # Send command
            self._sendLine('STORE %d %s' % (size, name))
            self._sendLine('Content-type: %s' % contentType)

            self._sendHeader('Content-Type', str(contentType))
            if expires is not None:
                epoch = time.mktime(expires.utctimetuple())
                self._sendHeader('File-Expires', str(int(epoch)))

            # Send blank line
            self._sendLine('')
            
            # Prepare to the upload the file
            bytesWritten = 0

            # Read in and upload the file 64kb at a time, by using the two-arg
            # form of iter (see
            # /usr/share/doc/python2.4/html/lib/built-in-funcs.html#l2h-42).
            for chunk in iter(lambda: file.read(1024*64), ''):
                self.f.write(chunk)
                bytesWritten += len(chunk)
            
            assert bytesWritten == size, (
                'size is %d, but %d were read from the file' 
                % (size, bytesWritten))
            self.f.flush()

            # Read response
            response = self.f.readline().strip()
            if not response.startswith('200'):
                raise UploadFailed, 'Server said: ' + response

            status, ids = response.split()
            contentID, aliasID = ids.split('/', 1)

            base = config.librarian.download_url
            path = '/%d/%s' % (int(aliasID), quote(name))
            return urljoin(base, path)
        finally:
            self._close()


def quote(s):
    # TODO: Perhaps filenames with / in them should be disallowed?
    return urllib.quote(s).replace('/', '%2F')


class _File:
    """A wrapper around a file like object that has security assertions"""

    def __init__(self, file):
        self.file = file

    def read(self, chunksize=None):
        if chunksize is None:
            return self.file.read()
        else:
            return self.file.read(chunksize)

    def close(self):
        return self.file.close()


class FileDownloadClient:
    """A simple client to download files from the librarian"""

    # If anything is using this, it should be exposed as a public method
    # in the interface. Note that there is no need to contact the Librarian
    # to do this if you have a database connection available.
    #
    # def _findByDigest(self, hexdigest):
    #     """Return a list of relative paths to aliases"""
    #     host = config.librarian.download_host
    #     port = config.librarian.download_port
    #     url = ('http://%s:%d/search?digest=%s' % (
    #         host, port, hexdigest)
    #         )
    #     results = urllib2.urlopen(url).read()
    #     lines = results.split('\n')
    #     count, paths = lines[0], lines[1:]
    #     if int(count) != len(paths):
    #         raise DownloadFailed, 'Incomplete response'
    #     return paths

    def _getPathForAlias(self, aliasID):
        """Returns the path inside the librarian to talk about the given
        alias.

        :param aliasID: A unique ID for the alias

        :returns: String path, url-escaped.  Unicode is UTF-8 encoded before
            url-escaping, as described in section 2.2.5 of RFC 2718.
            None if the file has been deleted.

        :raises: DownloadFailed if the alias is invalid
        """
        aliasID = int(aliasID)
        q = """
            SELECT filename, deleted
            FROM LibraryFileAlias, LibraryFileContent
            WHERE LibraryFileContent.id = LibraryFileAlias.content
                AND LibraryFileAlias.id = %d
            """ % aliasID
        cur = cursor()
        cur.execute(q)
        row = cur.fetchone()
        if row is None:
            raise DownloadFailed('Alias %d not found' % aliasID)
        filename, deleted = row
        if deleted:
            return None
        return '/%d/%s' % (aliasID, quote(filename.encode('utf-8')))

    def getURLForAlias(self, aliasID, is_buildd=False):
        """Returns the url for talking to the librarian about the given
        alias.

        :param aliasID: A unique ID for the alias

        :returns: String URL, or None if the file has expired and been deleted.
        """
        path = self._getPathForAlias(aliasID)
        if path is None:
            return None
        base = config.librarian.download_url
        if is_buildd:
            base = config.librarian.buildd_download_url
        return urljoin(base, path)

    def getFileByAlias(self, aliasID):
        """Returns a fd to read the file from

        :param aliasID: A unique ID for the alias

        :returns: file-like object, or None if the file has expired and
                  been deleted.
        """
        url = self.getURLForAlias(aliasID)
        if url is None:
            # File has been deleted
            return None
        try:
            return _File(urllib2.urlopen(url))
        except urllib2.HTTPError, x:
            if x.code == 404:
                raise LookupError, aliasID
            else:
                raise


class LibrarianClient(FileUploadClient, FileDownloadClient):
    """Object combining the upload/download interfaces to the Librarian
       simplifying access. This object is instantiated as a Utility
       using getUtility(ILibrarianClient)
    """

