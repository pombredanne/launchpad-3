# Copyright 2004 Canonical Ltd.  All rights reserved.
#

from socket import socket, SOCK_STREAM, AF_INET
from select import select

import urllib, urllib2

__all__ = ['UploadFailed', 'FileUploadClient', 'FileDownloadClient']

class UploadFailed(Exception):
    pass


class FileUploadClient(object):
    """Simple blocking client for uploading to the librarian."""

    def connect(self, host, port):
        """Connect this client to a particular host and port"""
        self.s = socket(AF_INET, SOCK_STREAM)
        self.s.connect((host, port))
        self.f = self.s.makefile('w+', 0)

    def _checkError(self):
        if select([self.s], [], [], 0)[0]:
            response = self.f.readline().strip()
            raise UploadFailed, 'Server said: ' + response
            
    def _sendLine(self, line):
        self.f.write(line + '\r\n')
        self._checkError()

    def addFile(self, name, size, file, contentType=None, digest=None):
        """Add a file to the librarian.

        :param name: Name to store the file as
        :param size: Size of the file
        :param file: File-like object with the content in it
        :param contentType: Optional mime-type, e.g. text/plain
        :param digest: Optional SHA-1 digest as hex string.  If given, the
            server will use this to check that the upload is not corrupt

        :raises UploadFailed: If the server rejects the upload for some reason
        """
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

        # Read response
        response = self.f.readline().strip()
        code, value = response.split(' ', 1)
        if code == '200':
            return value.split('/', 1)
        else:
            raise UploadFailed, 'Server said: ' + response

def quote(s):
    # TODO: Perhaps filenames with / in them should be disallowed?
    return urllib.quote(s).replace('/', '%2F')

class FileDownloadClient(object):
    """A simple client to download files from the librarian"""
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def getFile(self, fileID, aliasID, filename):
        """Returns a fd to read the file from
        
        :param fileID: A unique ID for the file content to download
        :param aliasID: A unique ID for the alias
        :param flename: The filename of the file being downloaded

        :returns: file-like object
        """
        
        url = ('http://%s:%d/%s/%s/%s'
               % (self.host, self.port, fileID, aliasID, quote(filename)))
        return urllib2.urlopen(url)

    def _findByDigest(self, hexdigest):
        """Return a list of relative paths to aliases"""
        url = ('http://%s:%d/search?digest=%s' % (self.host, self.port, hexdigest))
        results = urllib2.urlopen(url).read()
        lines = results.split('\n')
        count, paths = lines[0], lines[1:]
        # FIXME: raise exception if count != len(paths)
        return paths

    def findByDigest(self, hexdigest):
        """Find a file by its SHA-1 digest

        :returns: sequence of 3-tuples of (fileID, aliasID, filename).
        """
        return [p.split('/') for p in self._findByDigest(hexdigest)]

    def findLinksByDigest(self, hexdigest):
        """Return a list of URIs to file aliases matching 'hexdigest'"""
        return [('http://%s:%d/%s' % (self.host, self.port, path))
                for path in self._findByDigest(hexdigest)]

    def getPathForAlias(self, aliasID):
        """Returns the path inside the librarian to talk about the given
        alias.

        :param aliasID: A unique ID for the alias

        :returns: String Path
        """
        url = ('http://%s:%d/byalias?alias=%s'
               % (self.host, self.port, aliasID))
        f = urllib2.urlopen(url)
        l = f.read()[:-1] # Trim the newline
        f.close()

        return l
    
    def getURLForAlias(self, aliasID):
        """Returns the url for talking to the librarian about the given
        alias.

        :param aliasID: A unique ID for the alias

        :returns: String URL
        """
        l = self.getPathForAlias(aliasID)
        url = ('http://%s:%d%s' % (self.host, self.port, l))
        return url

    def getFileByAlias(self, aliasID):
        """Returns a fd to read the file from

        :param aliasID: A unique ID for the alias

        :returns: file-like object
        """
        url = self.getURLForAlias(aliasID)
        return urllib2.urlopen(url)
    
    
if __name__ == '__main__':
    import os, sys, sha
    uploader = FileUploadClient()
    uploader.connect('localhost', 9090)
    name = sys.argv[1]
    print 'Uploading', name, 'to localhost:9090'
    fileobj = open(name, 'rb')
    size = os.stat(name).st_size
    digest = sha.sha(open(name, 'rb').read()).hexdigest()
    fileid, filealias = uploader.addFile(name, size, fileobj,
                                         contentType='test/test', digest=digest)
    print 'Done.  File ID:',  fileid
    print 'File AliasID:', filealias

    downloader = FileDownloadClient('localhost', 8000)
    fp = downloader.getFile(fileid, filealias, name)
    print 'First 50 bytes:', repr(fp.read(50))
    print
    print downloader.findByDigest(digest)
