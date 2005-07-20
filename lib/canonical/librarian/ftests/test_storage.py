# Copyright 2004 Canonical Ltd.  All rights reserved.
#

import sha
import shutil
import tempfile
import unittest

from canonical.librarian.storage import LibrarianStorage, DigestMismatchError
from canonical.librarian.storage import LibraryFileUpload, DuplicateFileIDError
from canonical.librarian import db
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestSetup
from canonical.database.sqlbase import begin
from canonical.launchpad.database import LibraryFileContent, LibraryFileAlias


class LibrarianStorageDBTests(LaunchpadZopelessTestSetup, unittest.TestCase):
    dbuser = 'librarian'
    def __init__(self, methodName='runTest'):
        # We can't use super here, because: the signatures of the two __init__
        # functions are different.  Note also that unittest.TestCase doesn't use
        # super, so doesn't co-operate with properly with being called via
        # super, so it's lucky the setUp and tearDown methods of this class work
        # at all!
        unittest.TestCase.__init__(self, methodName)
        LaunchpadZopelessTestSetup.__init__(self)

    def setUp(self):
        super(LibrarianStorageDBTests, self).setUp()
        self.directory = tempfile.mkdtemp()
        self.storage = LibrarianStorage(self.directory, db.Library())

    def tearDown(self):
        shutil.rmtree(self.directory, ignore_errors=True)
        super(LibrarianStorageDBTests, self).tearDown()

    def test_addFile(self):
        data = 'data ' * 50
        digest = sha.sha(data).hexdigest()
        newfile = self.storage.startAddFile('file1', len(data))
        newfile.srcDigest = digest
        newfile.append(data)
        fileid, aliasid = newfile.store()
        self.failUnless(self.storage.hasFile(fileid))

    def test_addFiles_identical(self):
        # Start adding two files with identical data
        data = 'data ' * 5000
        digest = sha.sha(data).hexdigest()
        newfile1 = self.storage.startAddFile('file1', len(data))
        newfile2 = self.storage.startAddFile('file2', len(data))
        newfile1.append(data)
        newfile2.append(data)

        # Store the first...
        id1, alias1 = newfile1.store()

        # Now store the second, and make sure the second's temporary file is
        # *not* moved, i.e. it must be using the existing file
        def dontMove(x):
            self.fail("Second file should not be renamed")
        newfile2._move = dontMove
        id2, alias2 = newfile2.store()

        # Make sure we actually got an id
        self.assertNotEqual(None, id1)

        # And make sure both ids match
        self.assertEqual(id1, id2)

    def test_badDigest(self):
        data = 'data ' * 50
        digest = 'crud'
        newfile = self.storage.startAddFile('file', len(data))
        newfile.srcDigest = digest
        newfile.append(data)
        self.assertRaises(DigestMismatchError, newfile.store)

    def test_alias(self):
        # Add a file (and so also add an alias)
        data = 'data ' * 50
        digest = sha.sha(data).hexdigest()
        newfile = self.storage.startAddFile('file1', len(data))
        newfile.mimetype = 'text/unknown'
        newfile.append(data)
        fileid, aliasid = newfile.store()

        # Check that its alias has the right mimetype
        fa = self.storage.getFileAlias(fileid, 'file1')
        self.assertEqual('text/unknown', fa.mimetype)

        # Re-add the same file, with the same name and mimetype...
        newfile2 = self.storage.startAddFile('file1', len(data))
        newfile2.mimetype = 'text/unknown'
        newfile2.append(data)
        fileid2, aliasid2 = newfile2.store()

        # Verify that the new alias ID (and thus also name and mimetype) is in
        # fact the same as the first alias ID
        self.assertEqual(fa.id, self.storage.getFileAlias(fileid2, 'file1').id)

        # Now add the file again, with the same filename but different
        # mimetype...
        newfile3 = self.storage.startAddFile('file1', len(data))
        newfile3.mimetype = 'text/foo'
        newfile3.append(data)
        # ...which should work, and give us a new alias id
        fileid3, aliasid3 = newfile3.store()
        self.assertNotEqual(aliasid2, aliasid3)

    def test_clientProvidedDuplicateIDs(self):
        # This test checks the new behaviour specified by LibrarianTransactions
        # spec: don't create IDs in DB, but do check they don't exist.

        # Create a new file
        newfile = LibraryFileUpload(self.storage, 'filename', 0)

        # Set a content ID on the file (same as would happen with a
        # client-generated ID).
        newfile.contentID = 666

        # Make sure that _determineContentAndAliasIDs notices this is a new
        # file...
        new, contentID, aliasID = newfile._determineContentAndAliasIDs(None)
        self.assertEqual(True, new)
        # ...with the ID we gave it...
        self.assertEqual(666, contentID)
        # ...and the alias ID is irrelevant (it would be taken care of
        # client-side), so it should be None.
        self.assertEqual(None, aliasID)

        # Now manually add content ID 666 to the database, and commit.
        contentClash = LibraryFileContent(filesize=0, sha1='foo', id=666)
        self.txn.commit()

        # Now _determineContentAndAliasIDs will raise DuplicateFileIDError.
        self.assertRaises(DuplicateFileIDError,
                newfile._determineContentAndAliasIDs, None)

    def test_clientProvidedDuplicateContent(self):
        # Check the new behaviour specified by LibrarianTransactions spec: allow
        # duplicate content with distinct IDs.

        content = 'some content'

        # Store a file with id 6661
        newfile1 = LibraryFileUpload(self.storage, 'filename', 0)
        newfile1.contentID = 6661
        newfile1.append(content)
        fileid1, aliasid1 = newfile1.store()

        # Store second file identical to the first, with id 6662
        newfile2 = LibraryFileUpload(self.storage, 'filename', 0)
        newfile2.contentID = 6662
        newfile2.append(content)
        fileid2, aliasid2 = newfile2.store()

        # Create rows in the database for these files.
        content1 = LibraryFileContent(filesize=0, sha1='foo', id=6661)
        content2 = LibraryFileContent(filesize=0, sha1='foo', id=6662)
        self.txn.commit()

        # And no errors should have been raised!


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(LibrarianStorageDBTests))
    return suite

