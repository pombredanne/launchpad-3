# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Librarian garbage collection tests"""

__metaclass__ = type


import sys
import os
import os.path
from subprocess import Popen, PIPE, STDOUT
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

        # Make sure the files exist. We do this in setup, because we
        # need to use the get_file_path method later in the setup and we
        # want to be sure it is working correctly.
        path = librariangc.get_file_path(self.f1_id)
        self.failUnless(os.path.exists(path), "Librarian uploads failed")

        # Connect to the database as a user with file upload privileges
        self.ztm = initZopeless(
                dbuser=config.librarian.gc.dbuser, implicitBegin=False
                )

        # A value we use in a number of tests
        self.recent_past = (
                datetime.utcnow().replace(tzinfo=utc)
                - timedelta(days=6, hours=23)
                )

        # Make sure that every file the database knows about exists on disk.
        # We manually remove them for tests that need to cope with missing
        # library items.
        self.ztm.begin()
        cur = cursor()
        cur.execute("SELECT id FROM LibraryFileContent")
        for content_id in (row[0] for row in cur.fetchall()):
            path = librariangc.get_file_path(content_id)
            if not os.path.exists(path):
                open(path, 'w').write('whatever')
        self.ztm.abort()

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

        # Make sure the duplicates really are distinct
        self.failIfEqual(f1_id, f2_id)
        self.failIfEqual(f1.contentID, f2.contentID)

        # Set the last accessed time into the past so they will be garbage
        # collected
        past = datetime.utcnow() - timedelta(days=30)
        past = past.replace(tzinfo=utc)
        f1.last_accessed = past
        f2.last_accessed = past

        del f1, f2

        ztm.commit()
        ztm.uninstall()

        return f1_id, f2_id

    def test_MergeDuplicates(self):
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

    def test_DeleteUnreferencedAliases(self):
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
        self.assertRaises(SQLObjectNotFound, LibraryFileAlias.get, self.f1_id)
        self.assertRaises(SQLObjectNotFound, LibraryFileAlias.get, self.f2_id)

    def test_DeleteUnreferencedAliases2(self):
        # Don't delete LibraryFileAliases accessed recently

        # Merge the duplicates. Both our aliases now point to the same
        # LibraryFileContent
        librariangc.merge_duplicates(self.ztm)

        # Flag one of our LibraryFileAliases as being recently accessed
        self.ztm.begin()
        f1 = LibraryFileAlias.get(self.f1_id)
        f1.last_accessed = self.recent_past
        del f1
        self.ztm.commit()

        # Delete unreferenced LibraryFileAliases. This should remove neither
        # of our example aliases, as one of them was accessed recently
        librariangc.delete_unreferenced_aliases(self.ztm)

        # Make sure both our example files are still there
        self.ztm.begin()
        LibraryFileAlias.get(self.f1_id)
        LibraryFileAlias.get(self.f2_id)

    def test_DeleteUnreferencedAndWellExpiredAliases(self):
        # LibraryFileAliases can be removed after they have expired

        # Merge the duplicates. Both our aliases now point to the same
        # LibraryFileContent
        librariangc.merge_duplicates(self.ztm)

        # Flag one of our LibraryFileAliases with an expiry date in the past
        self.ztm.begin()
        f1 = LibraryFileAlias.get(self.f1_id)
        past = datetime.utcnow().replace(tzinfo=utc) - timedelta(days=30)
        f1.expires = past
        del f1
        self.ztm.commit()

        # Delete unreferenced LibraryFileAliases. This should remove our
        # example aliases, as one is unreferenced with a NULL expiry and
        # the other is unreferenced with an expiry in the past.
        librariangc.delete_unreferenced_aliases(self.ztm)

        # Make sure both our example files are gone
        self.ztm.begin()
        self.assertRaises(SQLObjectNotFound, LibraryFileAlias.get, self.f1_id)
        self.assertRaises(SQLObjectNotFound, LibraryFileAlias.get, self.f2_id)

    def test_DoneDeleteUnreferencedButNotExpiredAliases(self):
        # LibraryFileAliases can be removed only after they have expired.
        # If an explicit expiry is set and in recent past (currently up to
        # one week ago), the files hang around.

        # Merge the duplicates. Both our aliases now point to the same
        # LibraryFileContent
        librariangc.merge_duplicates(self.ztm)

        # Flag one of our LibraryFileAliases with an expiry date in the
        # recent past.
        self.ztm.begin()
        f1 = LibraryFileAlias.get(self.f1_id)
        f1.expires = self.recent_past
        del f1
        self.ztm.commit()

        # Delete unreferenced LibraryFileAliases. This should not remove our
        # example aliases, as one is unreferenced with a NULL expiry and
        # the other is unreferenced with an expiry in the recent past.
        librariangc.delete_unreferenced_aliases(self.ztm)

        # Make sure both our example files are still there
        self.ztm.begin()
        LibraryFileAlias.get(self.f1_id, None)
        LibraryFileAlias.get(self.f2_id, None)

    def test_DeleteUnreferencedContent(self):
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
 
    def test_DeleteUnreferencedContent2(self):
        # Like testDeleteUnreferencedContent, except that the file is
        # removed from disk before attempting to remove the unreferenced
        # LibraryFileContent.
        #
        # Because the garbage collector will remove an unreferenced file from
        # disk before it commits the database changes, it is possible that the
        # db removal will fail (eg. an exception was raised on COMMIT) leaving
        # the rows untouched in the database but no file on disk.
        # This is fine, as the next gc run will attempt it again and
        # nothing can use unreferenced files anyway. This test ensures
        # that this all works.

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

    def test_cronscript(self):
        script_path = os.path.join(
                config.root, 'cronscripts', 'librarian-gc.py'
                )
        cmd = [sys.executable, script_path, '-q']
        process = Popen(cmd, stdout=PIPE, stderr=STDOUT, stdin=PIPE)
        (script_output, _empty) = process.communicate()
        self.failUnlessEqual(process.returncode, 0)
        self.failUnlessEqual(script_output, '')

        # Make sure that our example files have been garbage collected
        self.ztm.begin()
        self.assertRaises(SQLObjectNotFound, LibraryFileAlias.get, self.f1_id)
        self.assertRaises(SQLObjectNotFound, LibraryFileAlias.get, self.f2_id)

        # And make sure stuff that *is* referenced remains
        LibraryFileAlias.get(2)
        cur = cursor()
        cur.execute("SELECT count(*) FROM LibraryFileAlias")
        count = cur.fetchone()[0]
        self.failIfEqual(count, 0)
        cur.execute("SELECT count(*) FROM LibraryFileContent")
        count = cur.fetchone()[0]
        self.failIfEqual(count, 0)

 
def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(TestLibrarianGarbageCollection))
    return suite
