# Copyright 2004 Canonical Ltd.  All rights reserved.
#

import unittest

from canonical.librarian import db

def sorted(l):
    l = list(l)
    l.sort()
    return l

class DBTestCase(unittest.TestCase):

    def setUp(self):
        from canonical.database.sqlbase import SQLBase
        from sqlobject import connectionForURI
        SQLBase.initZopeless(connectionForURI('postgres:///launchpad_test'))
        # Purge the tables; it's not like the launchpad_test db is important :)
        db.LibraryFileAlias.clearTable()
        db.LibraryFileContent.clearTable()

    def test_lookupByDigest(self):
        # Create library
        library = db.Library()

        # Initially it should be empty
        self.assertEqual([], library.lookupBySHA1('deadbeef'))

        # Add a file, check it is found by lookupBySHA1
        fileID, txn = library.add('deadbeef', 1234)
        txn.commit()
        self.assertEqual([fileID], library.lookupBySHA1('deadbeef'))

        # Add a new file with the same digest
        newFileID, newtxn = library.add('deadbeef', 1234)
        newtxn.commit()
        # Check it gets a new ID anyway
        self.assertNotEqual(fileID, newFileID)
        # Check it is found by lookupBySHA1
        self.assertEqual(sorted([fileID, newFileID]),
                sorted(library.lookupBySHA1('deadbeef')))

        aliasID = library.addAlias(fileID, 'file1', 'text/unknown')
        alias = library.getAlias(fileID, 'file1')
        self.assertEqual('file1', alias.filename)
        self.assertEqual('text/unknown', alias.mimetype)
        

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(DBTestCase))
    return suite
