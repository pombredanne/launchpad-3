# Copyright 2004 Canonical Ltd.  All rights reserved.
#

import unittest
#from zope.testing.doctestunit import DocTestSuite

from cStringIO import StringIO
import os
import rfc822
import sha
import shutil
import tempfile

from canonical.librarian.storage import FatSamStorage, DigestMismatchError
from canonical.librarian.storage import sameFile
from canonical.librarian import db
from canonical.lp import initZopeless

class FatSamStorageTests(unittest.TestCase):
    def setUp(self):
        import sys; sys.stdout.flush()
        import sys; sys.stderr.flush()
        from canonical.database.sqlbase import SQLBase
        initZopeless()
        self.directory = tempfile.mkdtemp()
        self.storage = FatSamStorage(self.directory, db.Library())
        db.LibraryFileAlias.clearTable()
        db.LibraryFileContent.clearTable()

    def tearDown(self):
        shutil.rmtree(self.directory, ignore_errors=True)

    def test_hasFile_missing(self):
        self.failIf(self.storage.hasFile("file that doesn't exist"))

    def test_addFile(self):
        data = 'data ' * 50
        digest = sha.sha(data).hexdigest()
        newfile = self.storage.startAddFile('file1', len(data))
        newfile.srcDigest = digest
        newfile.append(data)
        fileid, aliasid = newfile.store()
        self.failUnless(self.storage.hasFile(fileid))

    def test_addFiles_identical(self):
        data = 'data ' * 5000
        digest = sha.sha(data).hexdigest()
        newfile1 = self.storage.startAddFile('file1', len(data))
        newfile2 = self.storage.startAddFile('file2', len(data))
        newfile1.append(data)
        newfile2.append(data)
        id1, alias1 = newfile1.store()
        def dontMove(x):
            self.fail("Second file should not be renamed")
        newfile2._move = dontMove
        id2, alias2 = newfile2.store()
        self.assertNotEqual(None, id1)
        self.assertEqual(id1, id2)

    def test_badDigest(self):
        data = 'data ' * 50
        digest = 'crud'
        newfile = self.storage.startAddFile('file', len(data))
        newfile.srcDigest = digest
        newfile.append(data)
        self.assertRaises(DigestMismatchError, newfile.store)

    def test_sameFile(self):
        fd1, path1 = tempfile.mkstemp()
        fd2, path2 = tempfile.mkstemp()
        file1 = os.fdopen(fd1, 'wb')
        file2 = os.fdopen(fd2, 'wb')
        file1.write('data ' * 5000)
        file2.write('data ' * 5000)
        file1.close()
        file2.close()
        try:
            self.assert_(sameFile(path1, path2))
        finally:
            os.remove(path1)
            os.remove(path2)
        
    def test_differentFileShorter(self):
        fd1, path1 = tempfile.mkstemp()
        fd2, path2 = tempfile.mkstemp()
        file1 = os.fdopen(fd1, 'wb')
        file2 = os.fdopen(fd2, 'wb')
        file1.write('data ' * 5000)
        file2.write('data ' * 4999)
        file1.close()
        file2.close()
        try:
            self.failIf(sameFile(path1, path2))
        finally:
            os.remove(path1)
            os.remove(path2)
        
    def test_differentFileLonger(self):
        fd1, path1 = tempfile.mkstemp()
        fd2, path2 = tempfile.mkstemp()
        file1 = os.fdopen(fd1, 'wb')
        file2 = os.fdopen(fd2, 'wb')
        file1.write('data ' * 5000)
        file2.write('data ' * 5001)
        file1.close()
        file2.close()
        try:
            self.failIf(sameFile(path1, path2))
        finally:
            os.remove(path1)
            os.remove(path2)
        
    def test_transactionCommit(self):
        self.storage.library = StubLibrary()
        data = 'data ' * 50
        digest = sha.sha(data).hexdigest()
        newfile = self.storage.startAddFile('file1', len(data))
        newfile.append(data)
        fileid, aliasid = newfile.store()
        self.failUnless(self.storage.library.committed)
        self.failIf(os.path.exists(newfile.tmpfilepath))
        self.failUnless(self.storage.hasFile(fileid))
        
    def test_transactionAbort(self):
        self.storage.library = StubLibrary()
        data = 'data ' * 50
        digest = sha.sha(data).hexdigest()
        newfile = self.storage.startAddFile('file1', len(data))
        newfile.append(data)
        newfile._move = lambda x: 1/0  # Cause the final rename to break
        self.assertRaises(ZeroDivisionError, newfile.store)
        self.failUnless(self.storage.library.rolledback)
        self.failIf(os.path.exists(newfile.tmpfilepath))

    def test_alias(self):
        data = 'data ' * 50
        digest = sha.sha(data).hexdigest()
        newfile = self.storage.startAddFile('file1', len(data))
        newfile.mimetype = 'text/unknown'
        newfile.append(data)
        fileid, aliasid = newfile.store()
        fa = self.storage.getFileAlias(fileid, 'file1')
        self.assertEqual('text/unknown', fa.mimetype)
        newfile2 = self.storage.startAddFile('file1', len(data))
        newfile2.mimetype = 'text/unknown'
        newfile2.append(data)
        fileid2, aliasid2 = newfile2.store()
        self.assertEqual(fa.id, self.storage.getFileAlias(fileid2, 'file1').id)
        newfile3 = self.storage.startAddFile('file1', len(data))
        newfile3.mimetype = 'text/foo'
        newfile3.append(data)
        # This content already has this filename with a different mimetype
        self.assertRaises(db.AliasConflict, newfile3.store)

    def test_prefixDirectories(self):
        fileLoc = self.storage._relFileLocation
        self.assertEqual('123/123', fileLoc('123'))
        self.assertEqual('12345/12345', fileLoc('12345'))
        self.assertEqual('12345/12345678', fileLoc('12345678'))

    def test_multipleFilesInOnePrefixedDirectory(self):
        # Check that creating 10000/100001 followed by 10000/100002 works
        # correctly.
        self.storage.library = StubLibrary2()
        data = 'data ' * 50
        newfile = self.storage.startAddFile('file', len(data))
        newfile.append(data)
        fileid1, aliasid = newfile.store()
        # First id from stub library should be 100001
        self.assertEqual(100001, fileid1)

        data += 'more data'
        newfile = self.storage.startAddFile('file', len(data))
        newfile.append(data)
        fileid2, aliasid = newfile.store()
        # First id from stub library should be 100002
        self.assertEqual(100002, fileid2)

        self.failUnless(self.storage.hasFile(fileid1))
        self.failUnless(self.storage.hasFile(fileid2))
        
#    def test_metadataFile(self):
#        data = 'data ' * 50
#        digest = sha.sha(data).hexdigest()
#        newfile = self.storage.startAddFile('file1', len(data))
#        newfile.append(data)
#        fileid = newfile.store()
#        metadataPath = self.storage._fileLocation(fileid) + '.metadata'
#        self.failUnless(os.path.exists(metadataPath))
#        metadata = rcfc822.Message(open(metadata))
#        self.failUnless(metadata['


class StubLibrary:
    # For test_transactionCommit/Abort

    def __init__(self):
        self.committed = False
        self.rolledback = False

    def lookupBySHA1(self, digest):
        return []

    def add(self, size, digest):
        return 99, self

    def addAlias(self, fileid, filename, mimetype, txn=None):
        pass

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolledback = True


class StubLibrary2(StubLibrary):
    id = 100000
    def add(self, size, digest):
        self.id += 1
        return self.id, self



def test_suite():
    suite = unittest.TestSuite()
    #def addTests(klass): suite.addTests(map(klass, klass.tests))
    #addTests(FatSamTests)
   
    # Disabled - tests are doing initZopeless and don't play well with the
    # z3 test harness (Bug 2077). 
    #suite.addTest(unittest.makeSuite(FatSamStorageTests))
    return suite

