# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
#

__metaclass__ = type

import os
import os.path
import sha
import errno
import tempfile

from canonical.database.sqlbase import begin, commit, rollback

__all__ = ['DigestMismatchError', 'LibrarianStorage', 'LibraryFileUpload',
           'DuplicateFileIDError',
           # _relFileLocation needed by other modules in this package.
           # Listed here to keep the import facist happy
           '_relFileLocation']

class DigestMismatchError(Exception):
    """The given digest doesn't match the SHA-1 digest of the file"""

class DuplicateFileIDError(Exception):
    """Given File ID already exists"""


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
    srcDigest = None
    mimetype = 'unknown/unknown'
    contentID = None
    aliasID = None
    expires = None

    def __init__(self, storage, filename, size):
        self.storage = storage
        self.filename = filename
        self.size = size

        # Create temporary file
        tmpfile, tmpfilepath = tempfile.mkstemp(dir=self.storage.incoming)
        self.tmpfile = os.fdopen(tmpfile, 'w')
        self.tmpfilepath = tmpfilepath
        self.digester = sha.new()

    def append(self, data):
        self.tmpfile.write(data)
        self.digester.update(data)

    def store(self):
        self.tmpfile.close()

        # Verify the digest matches what the client sent us
        dstDigest = self.digester.hexdigest()
        if self.srcDigest is not None and dstDigest != self.srcDigest:
            # TODO: Write test that checks that the file really is removed or
            # renamed, and can't possibly be left in limbo
            os.remove(self.tmpfilepath)
            raise DigestMismatchError, (self.srcDigest, dstDigest)

        begin()
        try:
            # If we havn't got a contentID, we need to create one and return
            # it to the client.
            if self.contentID is None:
                contentID = self.storage.library.add(dstDigest, self.size)
                aliasID = self.storage.library.addAlias(
                        contentID, self.filename, self.mimetype, self.expires
                        )
            else:
                contentID = self.contentID
                aliasID = None


        except:
            # Abort transaction and re-raise
            rollback()
            raise

        # Move file to final location
        try:
            self._move(contentID)
        except:
            # Abort DB transaction
            rollback()

            # Remove file
            os.remove(self.tmpfilepath)

            # Re-raise
            raise

        # Commit any DB changes
        commit()
        
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

    chunksIter = iter(lambda: (file1.read(4096), file2.read(4096)), ('', ''))
    for chunk1, chunk2 in chunksIter:
        if chunk1 != chunk2:
            return False
    return True


def _relFileLocation(fileid):
    h = "%08x" % int(fileid)
    return '%s/%s/%s/%s' % (h[:2], h[2:4], h[4:6], h[6:])
    
