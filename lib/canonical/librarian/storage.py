# Copyright 2004 Canonical Ltd.  All rights reserved.
#

__metaclass__ = type

import os
import os.path
import sha
import errno
import tempfile

from canonical.librarian import db


class DigestMismatchError(Exception):
    """The given digest doesn't match the SHA-1 digest of the file"""


class FatSamStorage:
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
    
    def _relFileLocation(self, fileid):
        h = "%08x" % int(fileid)
        return '%s/%s/%s/%s' % (h[:2],h[2:4],h[4:6],h[6:])
    
    def _fileLocation(self, fileid):
        return os.path.join(self.directory, self._relFileLocation(str(fileid)))

    def startAddFile(self, filename, size):
        return FatSamFile(self, filename, size)

    def getFileAlias(self, fileid, filename):
        return self.library.getAlias(fileid, filename)

class FatSamFile(object):
    srcDigest = None
    mimetype = 'unknown/unknown'
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

        # Find potentially matching files
        similarFiles = self.storage.library.lookupBySHA1(dstDigest)
        newFile = True
        if len(similarFiles) == 0:
            fileID, txn = self.storage.library.add(dstDigest, self.size)
        else:
            for candidate in similarFiles:
                candidatePath = self.storage._fileLocation(candidate)
                if sameFile(candidatePath, self.tmpfilepath):
                    # Found a file with the same content
                    fileID = candidate
                    txn = None
                    newFile = False
                    break
            else:
                # No matches -- we found a hash collision in SHA-1!
                fileID, txn = self.storage.library.add(dstDigest, self.size)

        alias = self.storage.library.addAlias(fileID, self.filename,
                                              self.mimetype, txn)
        #f = open(self.storage._fileLocation(fileID) + '.metadata', 'wb')
        #f.close()
        if newFile:
            # Move file to final location
            try:
                self._move(fileID)
            except:
                # Abort DB transaction
                if txn is not None:
                    txn.rollback()

                # Remove file
                os.remove(self.tmpfilepath)

                # Re-raise
                raise
            else:
                if txn is not None:
                   txn.commit()
	else:
            # Not a new file; perhaps a new alias. Commit the transaction
	    if txn is not None:
	        txn.commit()
        
        if txn is not None:
            # XXX: dsilvers 2004-10-13: Need to make this nicer
            # We release the connection to the pool here. Without
            # this call; we end up overloading the psql server and
            # we get refused new connections.
	    txn._makeObsolete()
	
        # Return the IDs
        return fileID, alias

    def _move(self, fileID):
        location = self.storage._fileLocation(fileID)
        try:
            os.makedirs(os.path.dirname(location))
        except OSError, e:
            # If the directory already exists, that's ok.
            if e.errno != errno.EEXIST:
                raise
        os.rename(self.tmpfilepath, location)

def sameFile(path1, path2):
    file1 = open(path1, 'rb')
    file2 = open(path2, 'rb')

    chunksIter = iter(lambda: (file1.read(4096), file2.read(4096)), ('', ''))
    for chunk1, chunk2 in chunksIter:
        if chunk1 != chunk2:
            return False
    return True

