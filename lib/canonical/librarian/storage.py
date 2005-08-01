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
           'DuplicateFileIDError']

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

    def getFileAlias(self, fileid, filename):
        return self.library.getAlias(fileid, filename)

class LibraryFileUpload(object):
    srcDigest = None
    mimetype = 'unknown/unknown'
    contentID = None

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
            # XXX: Figure out a better name for _determineContentAndAliasIDs
            #        - AndrewBennetts, 2005-03-24
            result = self._determineContentAndAliasIDs(dstDigest)
            newFile, contentID, aliasID = result
        except:
            # Abort transaction and re-raise
            rollback()
            raise

        if newFile:
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
            else:
                commit()
        else:
            # Not a new file; perhaps a new alias. Commit the transaction
            commit()
        
        # Return the IDs
        return contentID, aliasID

    def _determineContentAndAliasIDs(self, digest):
        if self.contentID is None:
            # Find potentially matching files
            # XXX: This is deprecated.  It should happen in the garbage
            #      collection cron job.  See LibrarianTransactions spec.
            #        - Andrew Bennetts, 2005-03-24.
            similarFiles = self.storage.library.lookupBySHA1(digest)
            newFile = True
            if len(similarFiles) == 0:
                contentID = self.storage.library.add(digest, self.size)
            else:
                for candidate in similarFiles:
                    candidatePath = self.storage._fileLocation(candidate)
                    if _sameFile(candidatePath, self.tmpfilepath):
                        # Found a file with the same content
                        contentID = candidate
                        newFile = False
                        break
                else:
                    # No matches -- we found a hash collision in SHA-1!
                    contentID = self.storage.library.add(digest, self.size)
        
            aliasID = self.storage.library.addAlias(contentID, self.filename,
                                                    self.mimetype)
        else:
            contentID = self.contentID
            aliasID = None
            newFile = True
        
            # ensure the content and alias don't already exist.
            if self.storage.library.hasContent(contentID):
                raise DuplicateFileIDError(
                        'content ID %d already exists' % contentID)
        
            # We don't need to add them to the DB; the client has done that
            # for us.

        return newFile, contentID, aliasID

    def _move(self, fileID):
        location = self.storage._fileLocation(fileID)
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
    return '%s/%s/%s/%s' % (h[:2],h[2:4],h[4:6],h[6:])
    
