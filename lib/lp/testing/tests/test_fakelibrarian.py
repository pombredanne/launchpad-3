# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the fake librarian."""

__metaclass__ = type

from StringIO import StringIO

import transaction
from transaction.interfaces import ISynchronizer
from zope.component import getUtility

from canonical.launchpad.database.librarian import LibraryFileAliasSet
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.librarian.client import LibrarianClient
from canonical.librarian.interfaces import ILibrarianClient
from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing import (
    DatabaseFunctionalLayer, LaunchpadFunctionalLayer)
from lp.testing import TestCaseWithFactory
from lp.testing.fakelibrarian import FakeLibrarian


class LibraryAccessScenarioMixin:
    """Simple Librarian uses that can be serviced by the FakeLibrarian.

    This tests the subset of the Librarian interface that is also
    implemented by the FakeLibrarian.  If your test needs anything more
    than this, then you want the real Librarian.
    """

    def _storeFile(self):
        """Store a file in the `FakeLibrarian`.

        :return: Tuple of filename, file contents, alias id.
        """
        name = self.factory.getUniqueString() + '.txt'
        text = self.factory.getUniqueString()
        alias_id = getUtility(ILibrarianClient).addFile(
            name, len(text), StringIO(text), 'text/plain')
        return name, text, alias_id

    def test_baseline(self):
        self.assertTrue(
            verifyObject(
                ILibrarianClient, getUtility(ILibrarianClient)))
        self.assertTrue(
            verifyObject(
                ILibraryFileAliasSet, getUtility(ILibraryFileAliasSet)))

    def test_insert_retrieve(self):
        name, text, alias_id = self._storeFile()
        self.assertIsInstance(alias_id, (int, long))

        transaction.commit()

        library_file = getUtility(ILibrarianClient).getFileByAlias(alias_id)
        self.assertEqual(text, library_file.read())

    def test_alias_set(self):
        name, text, alias_id = self._storeFile()

        retrieved_alias = getUtility(ILibraryFileAliasSet)[alias_id]

        self.assertEqual(alias_id, retrieved_alias.id)
        self.assertEqual(name, retrieved_alias.filename)

    def test_read(self):
        name, text, alias_id = self._storeFile()
        transaction.commit()

        retrieved_alias = getUtility(ILibraryFileAliasSet)[alias_id]
        retrieved_alias.open()
        self.assertEqual(text, retrieved_alias.read())

    def test_uncommitted_file(self):
        name, text, alias_id = self._storeFile()
        retrieved_alias = getUtility(ILibraryFileAliasSet)[alias_id]
        self.assertRaises(LookupError, retrieved_alias.open)

    def test_incorrect_upload_size(self):
        name = self.factory.getUniqueString()
        text = self.factory.getUniqueString()
        wrong_length = len(text) + 1
        self.assertRaises(
            AssertionError,
            getUtility(ILibrarianClient).addFile,
            name, wrong_length, StringIO(text), 'text/plain')


class TestFakeLibrarian(LibraryAccessScenarioMixin, TestCaseWithFactory):
    """Test the supported interface subset on the fake librarian."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestFakeLibrarian, self).setUp()
        self.fake_librarian = FakeLibrarian()
        self.fake_librarian.installAsLibrarian()

    def tearDown(self):
        super(TestFakeLibrarian, self).tearDown()
        self.fake_librarian.uninstall()

    def test_fake(self):
        self.assertTrue(verifyObject(ISynchronizer, self.fake_librarian))
        self.assertIsInstance(self.fake_librarian, FakeLibrarian)


class TestRealLibrarian(LibraryAccessScenarioMixin, TestCaseWithFactory):
    """Test the supported interface subset on the real librarian."""

    layer = LaunchpadFunctionalLayer

    def test_real(self):
        self.assertIsInstance(getUtility(ILibrarianClient), LibrarianClient)
        self.assertIsInstance(
            getUtility(ILibraryFileAliasSet), LibraryFileAliasSet)
