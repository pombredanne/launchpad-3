# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
#

__metaclass__ = type

import sha
import urllib
import urllib2
import warnings
from socket import socket, SOCK_STREAM, AF_INET
from select import select
from urlparse import urljoin

from canonical.config import config
from canonical.database.sqlbase import cursor
from canonical.librarian.interfaces import UploadFailed, DownloadFailed

# TODO: Nuke all deprecated methods and refactor sometime after May 2005
# assuming nobody comes up with use cases for keeping them. I didn't
# just refactor this because I suspect that this API is used by code with
# poor or no test coverage -- StuartBishop 20050413

import warnings

__all__ = ['FileUploadClient', 'FileDownloadClient', 'LibrarianClient']

class FileUploadClient:
    """Simple blocking client for uploading to the librarian."""

    def connect(self, *args, **kw):
        # TODO: Nuke this method sometime after May 2005 -- StuartBishop
        warnings.warn(
                'FileUploadClient.connect is not needed and will be removed',
                DeprecationWarning, stacklevel=2
                )

    def close(self, **kw):
        # TODO: Nuke this method sometime after May 2005 -- StuartBishop
        warnings.warn(
                'FileUploadClient.close is not needed and will be removed',
                DeprecationWarning, stacklevel=2
                )

    def _connect(self):
        """Connect this client.
        
        The host and port default to what is specified in the configuration
        """
        host = config.librarian.upload_host
        port = config.librarian.upload_port

        self.s = socket(AF_INET, SOCK_STREAM)
        self.s.connect((host, port))
        self.f = self.s.makefile('w+', 0)

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

    def addFile(self, name, size, file, contentType, digest=None, _warn=True):
        """Add a file to the librarian.

        :param name: Name to store the file as
        :param size: Size of the file
        :param file: File-like object with the content in it
        :param contentType: mime-type, e.g. text/plain

        :returns: 2-tuple of (contentID, aliasID) as ints.
        
        :raises UploadFailed: If the server rejects the upload for some reason,
            or the size is 0.
        """
        # Detect if this method was not called from the LibrarianClient
        #
        if _warn:
            warnings.warn(
                    'LibrarianClient should be used instead of '
                    'FileUploadClient, preferably using the ILibrarianClient '
                    'Utility.',
                    DeprecationWarning, stacklevel=2
                    )
        if file is None:
            raise TypeError('No data')
        if size <= 0:
            raise UploadFailed('No data')

        if isinstance(name, unicode):
            name = name.encode('utf-8')

        self._connect()
        try:
            # Import in this method to avoid a circular import
            from canonical.launchpad.database import LibraryFileContent
            from canonical.launchpad.database import LibraryFileAlias

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
                            mimetype=contentType)

            return contentID, aliasID
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

    _logger = None

    def __init__(self, host=None, port=None):
        # TODO: Nuke keyword arguments sometime after May 2005 -- StuartBishop
        if host is not None or port is not None:
            warnings.warn(
                    'FileDownloadClient.__init__ no longer takes arguments. '
                    'Ignored.', DeprecationWarning, stacklevel=2
                    )
        self._logger = None

    def _warning(self, msg, *args):
        if self._logger is not None:
            self._logger.warning(msg, *args)

    def getFile(self, fileID, aliasID, filename):
        """Returns a fd to read the file from

        :param fileID: A unique ID for the file content to download
        :param aliasID: A unique ID for the alias
        :param filename: The filename of the file being downloaded

        :returns: file-like object
        """
        warnings.warn(
                'FileDownloadClient.getFile is not needed and will '
                'be removed. Use LibraryClient.getFileByAlias',
                DeprecationWarning, stacklevel=2
                )
        base = config.librarian.download_url
        path = '/%s/%s/%s' % (fileID, aliasID, quote(filename))
        url = urljoin(base, path)
        return urllib2.urlopen(url)

    def _findByDigest(self, hexdigest):
        """Return a list of relative paths to aliases"""
        host = config.librarian.download_host
        port = config.librarian.download_port
        url = ('http://%s:%d/search?digest=%s' % (
            host, port, hexdigest)
            )
        results = urllib2.urlopen(url).read()
        lines = results.split('\n')
        count, paths = lines[0], lines[1:]
        if int(count) != len(paths):
            raise DownloadFailed, 'Incomplete response'
        return paths

    def _parsePath(path):
        fileID, aliasID, filename = path.split('/')
        return int(fileID), int(aliasID), filename
    _parsePath = staticmethod(_parsePath)

    def findByDigest(self, hexdigest):
        """Find a file by its SHA-1 digest

        :returns: sequence of 3-tuples of (fileID, aliasID, filename).
        """
        warnings.warn(
                'FileDownloadClient.findByDigest is not needed and will '
                'be removed', DeprecationWarning, stacklevel=2
                )
        return [self._parsePath(path) for path in self._findByDigest(hexdigest)]

    def findLinksByDigest(self, hexdigest):
        """Return a list of URIs to file aliases matching 'hexdigest'"""
        warnings.warn(
                'FileDownloadClient.findLinksByDigest is not needed and will '
                'be removed', DeprecationWarning, stacklevel=2
                )
        host = config.librarian.download_host
        port = config.librarian.download_port
        return [('http://%s:%d/%s' % (host, port, path))
                for path in self._findByDigest(hexdigest)]

    def getPathForAlias(self, aliasID):
        """Deprecated"""
        warnings.warn(
                'FileDownloadClient.getPathForAlias is not needed and will '
                'be removed', DeprecationWarning, stacklevel=2
                )
        return self._getPathForAlias(aliasID)

    def _getPathForAlias(self, aliasID):
        """Returns the path inside the librarian to talk about the given
        alias.

        :param aliasID: A unique ID for the alias

        :returns: String path, url-escaped.  Unicode is UTF-8 encoded before
            url-escaping, as described in section 2.2.5 of RFC 2718.
        """
        aliasID = int(aliasID)
        q = """
            SELECT c.id, a.filename
            FROM
                LibraryFileAlias AS a
                JOIN LibraryFileContent AS c ON c.id = a.content
            WHERE
                a.id = %d
            """ % aliasID
        cur = cursor()
        cur.execute(q)
        row = cur.fetchone()
        if row is None:
            raise DownloadFailed, 'Alias %r not found' % (aliasID,)
        contentID, filename = row
        return '/%d/%d/%s' % (contentID, aliasID, 
                              quote(filename.encode('utf-8')))

    def getURLForAlias(self, aliasID, is_buildd=False):
        """Returns the url for talking to the librarian about the given
        alias.

        :param aliasID: A unique ID for the alias

        :returns: String URL
        """
        base = config.librarian.download_url
        if is_buildd:
            base = config.librarian.buildd_download_url
        path = self._getPathForAlias(aliasID)
        return urljoin(base, path)

    def getFileByAlias(self, aliasID):
        """Returns a fd to read the file from

        :param aliasID: A unique ID for the alias

        :returns: file-like object
        """
        url = self.getURLForAlias(aliasID)
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
    def __init__(self):
        super(LibrarianClient, self).__init__()

    def addFile(self, name, size, file, contentType):
        """See ILibrarianClient.addFile"""
        # Override the FileUploadClient implementation as the method
        # signature and return value has changed.
        # TODO: FileUploadClient and FileDownloadClient should be removed,
        # with their code moved into the LibrarianClient class and deprecated
        # methods removed.
        r = super(LibrarianClient, self).addFile(
                name, size, file, contentType, _warn=False
                )
        return int(r[1])

