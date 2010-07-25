# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the fake librarian."""

__metaclass__ = type

from StringIO import StringIO
import transaction
from transaction.interfaces import ISynchronizer

from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.librarian.interfaces import (
    DownloadFailed, ILibrarianClient, UploadFailed)
from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory
from lp.testing.fakelibrarian import FakeLibrarian


class TestFakeLibrarian(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestFakeLibrarian, self).setUp()
        self.librarian = FakeLibrarian()
        transaction.manager.registerSynch(self.librarian)

    def tearDown(self):
        super(TestFakeLibrarian, self).tearDown()
        transaction.manager.unregisterSynch(self.librarian)

    def _storeFile(self):
        """Store a file in the `FakeLibrarian`.

        :return: Tuple of filename, file contents, alias id.
        """
        name = self.factory.getUniqueString()
        text = self.factory.getUniqueString()
        alias_id = self.librarian.addFile(
            name, len(text), StringIO(text), 'text/plain')
        return name, text, alias_id

    def test_baseline(self):
        self.assertTrue(verifyObject(ILibrarianClient, self.librarian))
        self.assertTrue(verifyObject(ILibraryFileAliasSet, self.librarian))
        self.assertTrue(verifyObject(ISynchronizer, self.librarian))

    def test_insert_retrieve(self):
        name, text, alias_id = self._storeFile()
        self.assertIsInstance(alias_id, (int, long))

        transaction.commit()

        self.assertEqual(text, self.librarian.getFileByAlias(alias_id).read())

    def test_alias_set(self):
        name, text, alias_id = self._storeFile()

        retrieved_alias = self.librarian[alias_id]

        self.assertEqual(alias_id, retrieved_alias.id)
        self.assertEqual(name, retrieved_alias.filename)

    def test_read(self):
        name, text, alias_id = self._storeFile()
        transaction.commit()

        retrieved_alias = self.librarian[alias_id]
        retrieved_alias.open()
        self.assertEqual(text, retrieved_alias.read())

    def test_uncommitted_file(self):
        name, text, alias_id = self._storeFile()
        retrieved_alias = self.librarian[alias_id]
        self.assertRaises(DownloadFailed, retrieved_alias.open)

    def test_incorrect_upload_size(self):
        name = self.factory.getUniqueString()
        text = self.factory.getUniqueString()
        wrong_length = len(text) + 1
        self.assertRaises(
            UploadFailed,
            self.librarian.addFile,
            name, wrong_length, StringIO(text), 'text/plain')
