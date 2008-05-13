# Copyright 2004 Canonical Ltd.  All rights reserved.
#

# XXX: Andrew Bennetts 2005-03-24:
#      This file can (and probably should) be re-written as a doctest file,
#      for better readability.

import unittest
#from zope.testing.doctestunit import DocTestSuite

import os
import sha
import shutil
import tempfile

from storm.store import Store
from storm.zope.interfaces import IZStorm
from zope.component import getUtility

from canonical.librarian.storage import LibrarianStorage
from canonical.librarian.storage import _sameFile, _relFileLocation
from canonical.librarian import db
from canonical.testing import LaunchpadZopelessLayer


class LibrarianStorageTestCase(unittest.TestCase):
    """Librarian test cases that don't involve the database"""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.storage = LibrarianStorage(self.directory, db.Library())

        # Hook the commit and rollback methods of the store.
        self.store = getUtility(IZStorm).get('main')
        self.committed = self.rolledback = False
        self.orig_commit = self.store.commit
        self.orig_rollback = self.store.rollback
        def commit():
            self.committed = True
            self.orig_commit()
        self.store.commit = commit
        def rollback():
            self.rolledback = True
            self.orig_rollback()
        self.store.rollback = rollback

    def tearDown(self):
        shutil.rmtree(self.directory, ignore_errors=True)
        del self.store.commit
        del self.store.rollback
        self.orig_commit = self.orig_rollback = None

    def test_hasFile_missing(self):
        # Make sure hasFile returns False when a file is missing
        self.failIf(self.storage.hasFile(9999999))

    def _sameFileTestHelper(self, data1, data2):
        # Make two temporary files
        fd1, path1 = tempfile.mkstemp()
        fd2, path2 = tempfile.mkstemp()
        file1 = os.fdopen(fd1, 'wb')
        file2 = os.fdopen(fd2, 'wb')

        # Put the test data in them, and close them
        file1.write(data1)
        file2.write(data2)
        file1.close()
        file2.close()

        # Do the test, and clean up afterwards
        try:
            return _sameFile(path1, path2)
        finally:
            os.remove(path1)
            os.remove(path2)

    def test_sameFile(self):
        # Make sure sameFile returns True when the files are the same
        self.failUnless(self._sameFileTestHelper('data ' * 5000,
                                                 'data ' * 5000))

    def test_notSameFile(self):
        # Make sure sameFile returns False when the files are different, even
        # if they are the same length.
        self.failIf(self._sameFileTestHelper('data ' * 5000, 'fred ' * 5000))

    def test_differentFileShorter(self):
        # Make sure sameFile returns False when the second file is shorter
        # than the first, even if they were the same up to that length.
        self.failIf(self._sameFileTestHelper('data ' * 5000, 'data ' * 4999))

    def test_differentFileLonger(self):
        # Make sure sameFile returns False when the second file is longer than
        # the first, even if they were the same up to that length.
        self.failIf(self._sameFileTestHelper('data ' * 5000, 'data ' * 5001))

    def test_prefixDirectories(self):
        # _relFileLocation splits eight hex digits across four path segments
        self.assertEqual('12/34/56/78', _relFileLocation(0x12345678))

        # less than eight hex digits will be padded
        self.assertEqual('00/00/01/23', _relFileLocation(0x123))

        # more than eight digits will make the final segment longer, if that
        # were to ever happen
        self.assertEqual('12/34/56/789', _relFileLocation(0x123456789))

    def test_transactionCommit(self):
        # Use a stub library that doesn't really use the DB, but does record
        # if the Storage tried to commit the transaction on the fake DB.
        self.storage.library = StubLibrary()
        data = 'data ' * 50
        digest = sha.sha(data).hexdigest()
        newfile = self.storage.startAddFile('file1', len(data))
        newfile.contentID = 99
        newfile.append(data)

        # The transaction shouldn't be committed yet...
        self.failIf(self.committed)

        # Now try to store the file
        fileid, aliasid = newfile.store()

        # ...but it should be committed now.
        self.failUnless(self.committed)

        # And the file should now be in its final location on disk, too..
        self.failUnless(self.storage.hasFile(fileid))
        # ...and no longer at the temporary location
        self.failIf(os.path.exists(newfile.tmpfilepath))

    def test_transactionAbort(self):
        # Use a stub library that doesn't really use the DB, but does record
        # if the Storage tried to commit the transaction on the fake DB.
        self.storage.library = StubLibrary()
        data = 'data ' * 50
        digest = sha.sha(data).hexdigest()
        newfile = self.storage.startAddFile('file1', len(data))
        newfile.contentID = 99
        newfile.append(data)

        # Cause the final step, the file rename, to break
        newfile._move = lambda x: 1/0

        # The transaction shouldn't have aborted yet...
        self.failIf(self.rolledback)

        # Now try to store the file, and catch the exception
        self.assertRaises(ZeroDivisionError, newfile.store)

        # ...and the transaction should have aborted.
        self.failUnless(self.rolledback)

        # And the file should have been removed from its temporary location
        self.failIf(os.path.exists(newfile.tmpfilepath))

    def test_multipleFilesInOnePrefixedDirectory(self):
        # Check that creating a file that will be saved in 11/11/11/11
        # followed by a file that will be saved in 11/11/11/12 works
        # correctly -- i.e that creating a file works both if the directory
        # already exists, and if the directory doesn't already exist.
        self.storage.library = StubLibrary2()
        data = 'data ' * 50
        newfile = self.storage.startAddFile('file', len(data))
        newfile.contentID = 0x11111111
        newfile.append(data)
        fileid1, aliasid = newfile.store()
        # First id from stub library should be 0x11111111
        self.assertEqual(0x11111111, fileid1)

        data += 'more data'
        newfile = self.storage.startAddFile('file', len(data))
        newfile.contentID = 0x11111112
        newfile.append(data)
        fileid2, aliasid = newfile.store()
        # Second id from stub library should be 0x11111112
        self.assertEqual(0x11111112, fileid2)

        # Did the files both get stored?
        self.failUnless(self.storage.hasFile(fileid1))
        self.failUnless(self.storage.hasFile(fileid2))


class StubLibrary:
    # Used by test_transactionCommit/Abort

    def lookupBySHA1(self, digest):
        return []

    def add(self, digest, size):
        return 99

    def addAlias(self, fileid, filename, mimetype):
        pass


class StubLibrary2(StubLibrary):
    # Used by test_multipleFilesInOnePrefixedDirectory

    id = 0x11111110

    def add(self, digest, size):
        self.id += 1
        return self.id


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(LibrarianStorageTestCase))
    return suite

