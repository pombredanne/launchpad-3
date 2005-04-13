# Copyright 2004 Canonical Ltd.  All rights reserved.
#

from socket import socket, SOCK_STREAM, AF_INET
from select import select

import urllib, urllib2, warnings

from canonical.config import config

# TODO: Nuke all deprecated methods and refactor sometime after May 2005
# assuming nobody comes up with use cases for keeping them. I didn't
# just refactor this because I suspect that this API is used by code with
# poor or no test coverage -- StuartBishop 20050413

__all__ = ['UploadFailed', 'FileUploadClient', 'FileDownloadClient']

class UploadFailed(Exception):
    pass


class DownloadFailed(Exception):
    pass


class FileUploadClient(object):
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

    def addFile(self, name, size, file, contentType=None, digest=None,
            _warn=True):
        """Add a file to the librarian.

        :param name: Name to store the file as
        :param size: Size of the file
        :param file: File-like object with the content in it
        :param contentType: Optional mime-type, e.g. text/plain
        :param digest: Optional SHA-1 digest as hex string.  If given, the
            server will use this to check that the upload is not corrupt

        :raises UploadFailed: If the server rejects the upload for some reason
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

        self._connect()
        try:
            # Send command
            self._sendLine('STORE %d %s' % (size, name))

            # Send headers
            if contentType is not None:
                self._sendLine('Content-Type: ' + contentType)
            if digest is not None:
                self._sendLine('SHA1-Digest: ' + digest)

            # Send blank line
            self._sendLine('')
            
            # Send file
            for chunk in iter(lambda: file.read(4096), ''):
                self.f.write(chunk)
            self.f.flush()

            # Read response
            response = self.f.readline().strip()
            code, value = response.split(' ', 1)
            if code == '200':
                return value.split('/', 1)
            else:
                raise UploadFailed, 'Server said: ' + response
        finally:
            self._close()


def quote(s):
    # TODO: Perhaps filenames with / in them should be disallowed?
    return urllib.quote(s).replace('/', '%2F')


class _File(object):
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


class FileDownloadClient(object):
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

    # -- StuartBishop 20050412
    def getFile(self, fileID, aliasID, filename):
        """Returns a fd to read the file from

        :param fileID: A unique ID for the file content to download
        :param aliasID: A unique ID for the alias
        :param flename: The filename of the file being downloaded

        :returns: file-like object
        """
        warnings.warn(
                'FileDownloadClient.getFile is not needed and will '
                'be removed. Use LibraryClient.getFileByAlias',
                DeprecationWarning, stacklevel=2
                )
        host = config.librarian.download_host
        port = config.librarian.download_port
        url = ('http://%s:%d/%s/%s/%s'
               % (host, port, fileID, aliasID, quote(filename)))
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

    def findByDigest(self, hexdigest):
        """Find a file by its SHA-1 digest

        :returns: sequence of 3-tuples of (fileID, aliasID, filename).
        """
        warnings.warn(
                'FileDownloadClient.findByDigest is not needed and will '
                'be removed', DeprecationWarning, stacklevel=2
                )
        return [tuple(p.split('/')) for p in self._findByDigest(hexdigest)]

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

        :returns: String Path
        """
        host = config.librarian.download_host
        port = config.librarian.download_port
        url = ('http://%s:%d/byalias?alias=%s'
               % (host, port, aliasID))
        self._warning('getPathForAlias: http get %s', url)
        f = urllib2.urlopen(url)
        l = f.read()
        f.close()
        if l == 'Not found':
            raise DownloadFailed, 'Alias %r not found' % (aliasID,)
        if l == 'Bad search':
            raise DownloadFailed, 'Bad search: ' + repr(aliasID)
        return l.rstrip()

    def getURLForAlias(self, aliasID):
        """Returns the url for talking to the librarian about the given
        alias.

        :param aliasID: A unique ID for the alias

        :returns: String URL
        """
        host = config.librarian.download_host
        port = config.librarian.download_port
        l = self._getPathForAlias(aliasID)
        url = ('http://%s:%d%s' % (host, port, l))
        return url

    def getFileByAlias(self, aliasID):
        """Returns a fd to read the file from

        :param aliasID: A unique ID for the alias

        :returns: file-like object
        """
        url = self.getURLForAlias(aliasID)
        return _File(urllib2.urlopen(url))

class LibrarianClient(FileUploadClient, FileDownloadClient):
    """Object combining the upload/download interfaces to the Librarian
       simplifying access. This object is instantiated as a Utility
       using getUtility(ILibrarianClient)
    """
    def __init__(self):
        super(LibrarianClient, self).__init__()

    def addFile(self, name, size, file, contentType=None):
        """See ILibrarianClient.addFile"""
        # Override the FileUploadClient implementation as the method
        # signature and return value has changed.
        # TODO: FileUploadClient and FileDownloadClient should be removed,
        # with their code moved into the LibrarianClient class and deprecated
        # methods removed.
        r = super(LibrarianClient, self).addFile(name, size, file, _warn=False)
        return int(r[1])

