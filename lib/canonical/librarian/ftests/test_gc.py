# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Librarian garbage collection tests"""

__metaclass__ = type


import os.path
from cStringIO import StringIO
from unittest import TestCase, TestSuite, makeSuite
from datetime import datetime, timedelta
from pytz import utc

from zope.component import getUtility

from canonical.librarian.ftests.harness import LibrarianTestSetup
from canonical.launchpad.ftests.harness import LaunchpadTestSetup
from canonical.librarian import librariangc
from canonical.librarian.client import LibrarianClient
from canonical.launchpad.database import LibraryFileAlias, LibraryFileContent
from canonical.lp import initZopeless
from canonical.config import config
from canonical.database.sqlbase import cursor, SQLObjectNotFound
from canonical.database.constants  import UTC_NOW

class MockLogger:
    def error(self, *args, **kw):
        raise RuntimeError("An error was indicated: %r %r" % (args, kw))

    def debug(self, *args, **kw):
        #print '%r %r' % (args, kw)
        pass

    def info(self, *args, **kw):
        #print '%r %r' % (args, kw)
        pass


class TestLibrarianGarbageCollection(TestCase):
    def setUp(self):
        LaunchpadTestSetup().setUp()
        LibrarianTestSetup().setUp()

        self.client = LibrarianClient()
        librariangc.log = MockLogger()

        self.f1_id, self.f2_id = self._makeDupes()

        # Connect to the database as a user with file upload privileges
        self.ztm = initZopeless(
                dbuser=config.librarian.gc.dbuser, implicitBegin=False
                )

    def tearDown(self):
        LibrarianTestSetup().tearDown()
        LaunchpadTestSetup().tearDown()
        librariangc.log = None
        self.ztm.uninstall()

    def _makeDupes(self):
        """Create two duplicate LibraryFileContent entries with one
        LibraryFileAlias each. Return the two LibraryFileAlias ids as a
        tuple.
        """
        # Connect to the database as a user with file upload privileges,
        # in this case the PostgreSQL default user who happens to be an
        # administrator on launchpad development boxes.
        ztm = initZopeless(dbuser='', implicitBegin=False)

        ztm.begin()
        # Add some duplicate files
        content = 'This is some content'
        f1_id = self.client.addFile(
                'foo.txt', len(content), StringIO(content), 'text/plain',
                )
        f1 = LibraryFileAlias.get(f1_id)
        f2_id = self.client.addFile(
                'foo.txt', len(content), StringIO(content), 'text/plain',
                )
        f2 = LibraryFileAlias.get(f2_id)

        # Make sure they really are duplicates
        self.failIfEqual(f1_id, f2_id)
        self.failIfEqual(f1.contentID, f2.contentID)

        # Set the last accessed time into the past so they will be garbage
        # collected
        past = datetime.now() - timedelta(days=30)
        past = past.replace(tzinfo=utc)
        f1.last_accessed = past
        f2.last_accessed = past

        del f1
        del f2

        ztm.commit()
        ztm.uninstall()

        return f1_id, f2_id

    def testMergeDuplicates(self):
        # Merge the duplicates
        librariangc.merge_duplicates(self.ztm)

        # merge_duplicates should have committed
        self.ztm.begin()
        self.ztm.abort()

        # Confirm that the duplicates have been merged
        self.ztm.begin()
        f1 = LibraryFileAlias.get(self.f1_id)
        f2 = LibraryFileAlias.get(self.f2_id)
        self.failUnlessEqual(f1.contentID, f2.contentID)

    def testDeleteUnreferencedAliases(self):
        self.ztm.begin()

        # Confirm that our sample files are there.
        f1 = LibraryFileAlias.get(self.f1_id)
        f2 = LibraryFileAlias.get(self.f2_id)
        # Grab the content IDs related to these unreferenced LibraryFileAliases
        c1_id = f1.contentID
        c2_id = f2.contentID
        del f1, f2
        self.ztm.abort()

        # Delete unreferenced aliases
        librariangc.delete_unreferenced_aliases(self.ztm)

        # This should have committed
        self.ztm.begin()

        # Confirm that the LibaryFileContents are still there
        c1 = LibraryFileContent.get(c1_id)
        c2 = LibraryFileContent.get(c2_id)

        # But the LibraryFileAliases should be gone
        try:
            LibraryFileAlias.get(self.f1_id, None)
            self.fail("LibraryFileAlias %d was not removed" % self.f1_id)
        except SQLObjectNotFound:
            pass
        try:
            LibraryFileAlias.get(self.f2_id, None)
            self.fail("LibraryFileAlias %d was not removed" % self.f2_id)
        except SQLObjectNotFound:
            pass

    def testDeleteUnreferrencedAliases2(self):
        # Don't delete LibraryFileAliases accessed recently

        # Merge the duplicates. Both our aliases now point to the same
        # LibraryFileContent
        librariangc.merge_duplicates(self.ztm)

        # Flag one of our LibraryFileAliase as being recently accessed
        self.ztm.begin()
        f1 = LibraryFileAlias.get(self.f1_id)
        f1.last_accessed = UTC_NOW
        del f1
        self.ztm.commit()

        # Delete unreferenced LibraryFileAliase. This should remove neither
        # of our example aliases, as one of them was accessed recently
        librariangc.delete_unreferenced_aliases(self.ztm)

        # Make sure both our example files are still there
        self.ztm.begin()
        LibraryFileAlias.get(self.f1_id)
        LibraryFileAlias.get(self.f2_id)

    def testDeleteUnreferencedContent(self):
        # Merge the duplicates. This creates an unreferenced LibraryFileContent
        librariangc.merge_duplicates(self.ztm)

        self.ztm.begin()

        # Locate the unreferenced LibraryFileContent
        cur = cursor()
        cur.execute("""
            SELECT LibraryFileContent.id
            FROM LibraryFileContent
            LEFT OUTER JOIN LibraryFileAlias
                ON LibraryFileContent.id = LibraryFileAlias.content
            WHERE LibraryFileAlias.id IS NULL
                AND LibraryFileContent.id IN (%d, %d)
            """ % (self.f1_id, self.f2_id))
        results = cur.fetchall()
        self.failUnlessEqual(len(results), 1)
        unreferenced_id = results[0][0]

        self.ztm.abort()

        # Make sure the file exists on disk
        path = librariangc.get_file_path(unreferenced_id)
        self.failUnless(os.path.exists(path))

        # Delete unreferenced content
        librariangc.delete_unreferenced_content(self.ztm)

        # Make sure the file is gone
        self.failIf(os.path.exists(path))

        # delete_unreferenced_content should have committed
        self.ztm.begin()

        # Make sure the unreferenced entries have all gone
        cur = cursor()
        cur.execute("""
            SELECT LibraryFileContent.id
            FROM LibraryFileContent
            LEFT OUTER JOIN LibraryFileAlias
                ON LibraryFileContent.id = LibraryFileAlias.content
            WHERE LibraryFileAlias.id IS NULL
            """)
        results = list(cur.fetchall())
        self.failUnlessEqual(
                len(results), 0, 'Too many results %r' % (results,)
                )
 
    def testDeleteUnreferencedContent2(self):
        # Like testDeleteUnreferencedContent, except that the file is
        # removed from disk before attempting to remove the unreferenced
        # LibraryFileContent. Because an unreferenced file is removed from
        # disk before the db row is removed, it is possible that the
        # db removal fails. This is fine, as the next gc run will attempt
        # it again and nothing can use unreferenced files anyway. This
        # test ensures that this works.

        # Merge the duplicates. This creates an unreferenced LibraryFileContent
        librariangc.merge_duplicates(self.ztm)

        self.ztm.begin()

        # Locate the unreferenced LibraryFileContent
        cur = cursor()
        cur.execute("""
            SELECT LibraryFileContent.id
            FROM LibraryFileContent
            LEFT OUTER JOIN LibraryFileAlias
                ON LibraryFileContent.id = LibraryFileAlias.content
            WHERE LibraryFileAlias.id IS NULL
                AND LibraryFileContent.id IN (%d, %d)
            """ % (self.f1_id, self.f2_id))
        results = cur.fetchall()
        self.failUnlessEqual(len(results), 1)
        unreferenced_id = results[0][0]

        self.ztm.abort()

        # Make sure the file exists on disk
        path = librariangc.get_file_path(unreferenced_id)
        self.failUnless(os.path.exists(path))

        # Remove the file from disk
        os.unlink(path)
        self.failIf(os.path.exists(path))

        # Delete unreferenced content
        librariangc.delete_unreferenced_content(self.ztm)

        # Make sure the file is gone
        self.failIf(os.path.exists(path))

        # delete_unreferenced_content should have committed
        self.ztm.begin()

        # Make sure the unreferenced entries have all gone
        cur = cursor()
        cur.execute("""
            SELECT LibraryFileContent.id
            FROM LibraryFileContent
            LEFT OUTER JOIN LibraryFileAlias
                ON LibraryFileContent.id = LibraryFileAlias.content
            WHERE LibraryFileAlias.id IS NULL
            """)
        results = list(cur.fetchall())
        self.failUnlessEqual(
                len(results), 0, 'Too many results %r' % (results,)
                )
 
def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(TestLibrarianGarbageCollection))
    return suite
