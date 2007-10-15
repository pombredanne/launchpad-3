# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
#

__metaclass__ = type

import os
import os.path
import md5
import sha
import errno
import tempfile

from canonical.database.sqlbase import begin, commit, rollback, cursor

__all__ = ['DigestMismatchError', 'LibrarianStorage', 'LibraryFileUpload',
           'DuplicateFileIDError', 'WrongDatabaseError',
           # _relFileLocation needed by other modules in this package.
           # Listed here to keep the import facist happy
           '_relFileLocation', '_sameFile']

class DigestMismatchError(Exception):
    """The given digest doesn't match the SHA-1 digest of the file."""


class DuplicateFileIDError(Exception):
    """Given File ID already exists."""


class WrongDatabaseError(Exception):
    """The client's database name doesn't match our database."""
    def __init__(self, clientDatabaseName, serverDatabaseName):
        self.clientDatabaseName = clientDatabaseName
        self.serverDatabaseName = serverDatabaseName
        self.args = (clientDatabaseName, serverDatabaseName)


class LibrarianStorage:
    """Blob storage.

    This manages the actual storage of files on disk and the record of those in
    the database; it has nothing to do with the network interface to those
    files.
    """

    def __init__(self, directory, library):
        self.directory = directory
        self.library = library
        self.incoming = os.path.join(self.directory, 'incoming')
        try:
            os.mkdir(self.incoming)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise

    def hasFile(self, fileid):
        return os.access(self._fileLocation(fileid), os.F_OK)

    def _fileLocation(self, fileid):
        return os.path.join(self.directory, _relFileLocation(str(fileid)))

    def startAddFile(self, filename, size):
        return LibraryFileUpload(self, filename, size)

    def getFileAlias(self, aliasid):
        return self.library.getAlias(aliasid)


class LibraryFileUpload(object):
    """A file upload from a client."""
    srcDigest = None
    mimetype = 'unknown/unknown'
    contentID = None
    aliasID = None
    expires = None
    databaseName = None
    debugID = None

    def __init__(self, storage, filename, size):
        self.storage = storage
        self.filename = filename
        self.size = size
        self.debugLog = []

        # Create temporary file
        tmpfile, tmpfilepath = tempfile.mkstemp(dir=self.storage.incoming)
        self.tmpfile = os.fdopen(tmpfile, 'w')
        self.tmpfilepath = tmpfilepath
        self.shaDigester = sha.new()
        self.md5Digester = md5.new()

    def append(self, data):
        self.tmpfile.write(data)
        self.shaDigester.update(data)
        self.md5Digester.update(data)

    def store(self):
        self.debugLog.append('storing %r, size %r' % (self.filename, self.size))
        self.tmpfile.close()

        # Verify the digest matches what the client sent us
        dstDigest = self.shaDigester.hexdigest()
        if self.srcDigest is not None and dstDigest != self.srcDigest:
            # XXX: Andrew Bennetts 2004-09-20: Write test that checks that
            # the file really is removed or renamed, and can't possibly be
            # left in limbo
            os.remove(self.tmpfilepath)
            raise DigestMismatchError, (self.srcDigest, dstDigest)

        begin()
        try:
            # If the client told us the name database of the database its using,
            # check that it matches
            if self.databaseName is not None:
                cur = cursor()
                cur.execute("SELECT current_database();")
                databaseName = cur.fetchone()[0]
                if self.databaseName != databaseName:
                    raise WrongDatabaseError(self.databaseName, databaseName)

            self.debugLog.append('database name %r ok' % (self.databaseName,))
            # If we haven't got a contentID, we need to create one and return
            # it to the client.
            if self.contentID is None:
                contentID = self.storage.library.add(
                        dstDigest, self.size, self.md5Digester.hexdigest())
                aliasID = self.storage.library.addAlias(
                        contentID, self.filename, self.mimetype, self.expires)
                self.debugLog.append('created contentID: %r, aliasID: %r.'
                                     % (contentID, aliasID))
            else:
                contentID = self.contentID
                aliasID = None
                self.debugLog.append('received contentID: %r' % (contentID,))

        except:
            # Abort transaction and re-raise
            self.debugLog.append('failed to get contentID/aliasID, aborting')
            rollback()
            raise

        # Move file to final location
        try:
            self._move(contentID)
        except:
            # Abort DB transaction
            self.debugLog.append('failed to move file, aborting')
            rollback()

            # Remove file
            os.remove(self.tmpfilepath)

            # Re-raise
            raise

        # Commit any DB changes
        commit()
        self.debugLog.append('committed')

        # Return the IDs if we created them, or None otherwise
        return contentID, aliasID

    def _move(self, fileID):
        location = self.storage._fileLocation(fileID)
        if os.path.exists(location):
            raise DuplicateFileIDError(fileID)
        try:
            os.makedirs(os.path.dirname(location))
        except OSError, e:
            # If the directory already exists, that's ok.
            if e.errno != errno.EEXIST:
                raise
        os.rename(self.tmpfilepath, location)


def _sameFile(path1, path2):
    file1 = open(path1, 'rb')
    file2 = open(path2, 'rb')

    blk = 1024 * 64
    chunksIter = iter(lambda: (file1.read(blk), file2.read(blk)), ('', ''))
    for chunk1, chunk2 in chunksIter:
        if chunk1 != chunk2:
            return False
    return True


def _relFileLocation(fileid):
    h = "%08x" % int(fileid)
    return '%s/%s/%s/%s' % (h[:2], h[2:4], h[4:6], h[6:])

