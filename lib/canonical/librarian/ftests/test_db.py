# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import unittest

import transaction
from zope.component import getUtility

from canonical.launchpad.database.librarian import LibraryFileContent
from canonical.launchpad.webapp.interfaces import (
        IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.librarian import db
from canonical.testing import LaunchpadZopelessLayer


class DBTestCase(unittest.TestCase):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.layer.switchDbUser('librarian')

    def test_lookupByDigest(self):
        # Create library
        library = db.Library()

        # Initially it should be empty
        self.assertEqual([], library.lookupBySHA1('deadbeef'))

        # Add a file, check it is found by lookupBySHA1
        fileID = library.add('deadbeef', 1234, 'abababab')
        self.assertEqual([fileID], library.lookupBySHA1('deadbeef'))

        # Add a new file with the same digest
        newFileID = library.add('deadbeef', 1234, 'abababab')
        # Check it gets a new ID anyway
        self.assertNotEqual(fileID, newFileID)
        # Check it is found by lookupBySHA1
        self.assertEqual(sorted([fileID, newFileID]),
                         sorted(library.lookupBySHA1('deadbeef')))

        aliasID = library.addAlias(fileID, 'file1', 'text/unknown')
        alias = library.getAlias(aliasID, None, '/')
        self.assertEqual('file1', alias.filename)
        self.assertEqual('text/unknown', alias.mimetype)


class TestTransactionDecorators(unittest.TestCase):
    """Tests for the transaction decorators used by the librarian."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.layer.switchDbUser('librarian')
        self.store = getUtility(IStoreSelector).get(
                MAIN_STORE, DEFAULT_FLAVOR)
        self.content_id = db.Library().add('deadbeef', 1234, 'abababab')
        self.file_content = self._getTestFileContent()
        transaction.commit()

    def _getTestFileContent(self):
        """Return the file content object that created."""
        return self.store.find(LibraryFileContent, id=self.content_id).one()

    def test_getAlias(self):
        # Library.getAlias() returns the LibrarayFileAlias for a given
        # LibrarayFileAlias ID.
        library = db.Library(restricted=False)
        alias = library.getAlias(1, None, '/')
        self.assertEqual(1, alias.id)

    def test_getAlias_no_such_record(self):
        # Library.getAlias() raises a LookupError, if no record with
        # the given ID exists.
        library = db.Library(restricted=False)
        self.assertRaises(LookupError, library.getAlias, -1, None, '/')

    def test_getAlias_content_is_null(self):
        # Library.getAlias() raises a LookupError, if no content
        # record for the given alias exists.
        library = db.Library(restricted=False)
        alias = library.getAlias(1, None, '/')
        alias.content = None
        self.assertRaises(LookupError, library.getAlias, 1, None, '/')

    def test_getAlias_content_is_none(self):
        # Library.getAlias() raises a LookupError, if the matching
        # record does not reference any LibraryFileContent record.
        library = db.Library(restricted=False)
        alias = library.getAlias(1, None, '/')
        alias.content = None
        self.assertRaises(LookupError, library.getAlias, 1, None, '/')

    def test_getAlias_content_wrong_library(self):
        # Library.getAlias() raises a LookupError, if a restricted
        # library looks up a unrestricted LibraryFileAlias and
        # vice versa.
        restricted_library = db.Library(restricted=True)
        self.assertRaises(
            LookupError, restricted_library.getAlias, 1, None, '/')

        unrestricted_library = db.Library(restricted=False)
        alias = unrestricted_library.getAlias(1, None, '/')
        alias.restricted = True
        self.assertRaises(
            LookupError, unrestricted_library.getAlias, 1, None, '/')

    def test_getAliases(self):
        # Library.getAliases() returns a sequence
        # [(LFA.id, LFA.filename, LFA.mimetype), ...] where LFA are
        # LibrarayFileAlias records having the given LibraryFileContent
        # ID.
        library = db.Library(restricted=False)
        aliases = library.getAliases(1)
        expected_aliases = [
            (1, u'netapplet-1.0.0.tar.gz', u'application/x-gtar'),
            (2, u'netapplet_1.0.0.orig.tar.gz', u'application/x-gtar'),
            ]
        self.assertEqual(expected_aliases, aliases)

    def test_getAliases_content_is_none(self):
        # Library.getAliases() does not return records which do not
        # reference any LibraryFileContent record.
        library = db.Library(restricted=False)
        alias = library.getAlias(1, None, '/')
        alias.content = None
        aliases = library.getAliases(1)
        expected_aliases = [
            (2, u'netapplet_1.0.0.orig.tar.gz', u'application/x-gtar'),
            ]
        self.assertEqual(expected_aliases, aliases)

    def test_getAliases_content_wrong_library(self):
        # Library.getAliases() does not return data from restriceded
        # LibrarayFileAlias records when called from a unrestricted
        # library and vice versa.
        unrestricted_library = db.Library(restricted=False)
        alias = unrestricted_library.getAlias(1, None, '/')
        alias.restricted = True

        aliases = unrestricted_library.getAliases(1)
        expected_aliases = [
            (2, u'netapplet_1.0.0.orig.tar.gz', u'application/x-gtar'),
            ]
        self.assertEqual(expected_aliases, aliases)

        restricted_library = db.Library(restricted=True)
        aliases = restricted_library.getAliases(1)
        expected_aliases = [
            (1, u'netapplet-1.0.0.tar.gz', u'application/x-gtar'),
            ]
        self.assertEqual(expected_aliases, aliases)

    def test_read_transaction_reset_store(self):
        """Make sure that the store is reset after the transaction."""
        @db.read_transaction
        def no_op():
            pass
        no_op()
        self.failIf(
            self.file_content is self._getTestFileContent(),
            "Store wasn't reset properly.")

    def test_write_transaction_reset_store(self):
        """Make sure that the store is reset after the transaction."""
        @db.write_transaction
        def no_op():
            pass
        no_op()
        self.failIf(
            self.file_content is self._getTestFileContent(),
            "Store wasn't reset properly.")

    def test_write_transaction_reset_store_with_raise(self):
        """Make sure that the store is reset after the transaction."""
        @db.write_transaction
        def no_op():
            raise RuntimeError('an error occured')
        self.assertRaises(RuntimeError, no_op)
        self.failIf(
            self.file_content is self._getTestFileContent(),
            "Store wasn't reset properly.")

    def test_writing_transaction_reset_store_on_commit_failure(self):
        """The store should be reset even if committing the transaction fails.
        """
        class TransactionAborter:
            """Make the next commit() fails."""
            def newTransaction(self, txn):
                pass

            def beforeCompletion(self, txn):
                raise RuntimeError('the commit will fail')
        aborter = TransactionAborter()
        transaction.manager.registerSynch(aborter)
        try:
            @db.write_transaction
            def no_op():
                pass
            self.assertRaises(RuntimeError, no_op)
            self.failIf(
                self.file_content is self._getTestFileContent(),
                "Store wasn't reset properly.")
        finally:
            transaction.manager.unregisterSynch(aborter)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
