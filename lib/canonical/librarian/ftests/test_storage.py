# Copyright 2004 Canonical Ltd.  All rights reserved.
#

import sha
import shutil
import tempfile
import unittest

from canonical.librarian.storage import FatSamStorage, DigestMismatchError
from canonical.librarian import db
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestSetup
from canonical.database.sqlbase import begin


class FatSamStorageDBTests(LaunchpadZopelessTestSetup, unittest.TestCase):
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
        super(FatSamStorageDBTests, self).setUp()
        self.directory = tempfile.mkdtemp()
        self.storage = FatSamStorage(self.directory, db.Library())

    def tearDown(self):
        shutil.rmtree(self.directory, ignore_errors=True)
        from canonical.database.sqlbase import begin
        begin()
        super(FatSamStorageDBTests, self).tearDown()

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
        # ...so when we store it, we get an AliasConflict
        self.assertRaises(db.AliasConflict, newfile3.store)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(FatSamStorageDBTests))
    return suite

