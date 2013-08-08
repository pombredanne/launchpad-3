# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Librarian disk to Swift storage tests."""

__metaclass__ = type

from cStringIO import StringIO
import os.path

from mock import patch
import transaction

from lp.services.database.interfaces import IStore
from lp.services.features.testing import FeatureFixture
from lp.services.librarian.client import LibrarianClient
from lp.services.librarian.model import LibraryFileAlias
from lp.services.log.logger import BufferLogger
from lp.testing import TestCase
from lp.testing.layers import LaunchpadZopelessLayer, LibrarianLayer
from lp.testing.swift.fixture import SwiftFixture

from lp.services.librarianserver import swift


class TestFeedSwift(TestCase):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestFeedSwift, self).setUp()
        self.swift_fixture = self.useFixture(SwiftFixture())
        self.useFixture(FeatureFixture({'librarian.swift.enabled': True}))
        transaction.commit()

        # Restart the Librarian so it picks up the OS_* environment
        # variables.
        LibrarianLayer.librarian_fixture.killTac()
        LibrarianLayer.librarian_fixture.setUp()

        # Add some files.
        self.librarian_client = LibrarianClient()
        self.contents = [str(i) * i for i in range(1, 5)]
        self.lfa_ids = [
            self.librarian_client.addFile(
                name='file_{}'.format(i),
                size=len(content), file=StringIO(content),
                contentType='text/plain') for content in self.contents]
        self.lfas = [
            IStore(LibraryFileAlias).get(LibraryFileAlias, lfa_id)
                for lfa_id in self.lfa_ids]
        self.lfcs = [lfa.content for lfa in self.lfas]
        transaction.commit()

    def tearDown(self):
        super(TestFeedSwift, self).tearDown()
        # Restart the Librarian so it picks up the feature flag change.
        LibrarianLayer.librarian_fixture.killTac()
        LibrarianLayer.librarian_fixture.setUp()

    def test_copy_to_swift(self):
        log = BufferLogger()

        # Confirm that files exist on disk where we expect to find them.
        for lfc in self.lfcs:
            path = swift.filesystem_path(lfc.id)
            self.assert_(os.path.exists(path))

        # Copy all the files into Swift.
        swift.to_swift(log)  # remove == False

        # Confirm that files exist on disk where we expect to find them.
        for lfc in self.lfcs:
            path = swift.filesystem_path(lfc.id)
            self.assert_(os.path.exists(path))

        # Confirm all the files are also in Swift.
        swift_client = self.swift_fixture.connect()
        for lfc, contents in zip(self.lfcs, self.contents):
            container, name = swift.swift_location(lfc.id)
            headers, obj = swift_client.get_object(container, name)
            self.assertEqual(contents, obj, 'Did not round trip')

        # Running again does nothing, in particular does not reupload
        # the files to Swift.
        con_patch = patch.object(
            swift.swiftclient.Connection, 'put_object',
            side_effect=AssertionError('do not call'))
        with con_patch:
            swift.to_swift(log)  # remove == False

    def test_move_to_swift(self):
        log = BufferLogger()

        # Confirm that files exist on disk where we expect to find them.
        for lfc in self.lfcs:
            path = swift.filesystem_path(lfc.id)
            self.assert_(os.path.exists(path))

        # Migrate all the files into Swift.
        swift.to_swift(log, remove=True)

        # Confirm that all the files have gone from disk.
        for lfc in self.lfcs:
            self.failIf(os.path.exists(swift.filesystem_path(lfc.id)))

        # Confirm all the files are in Swift.
        swift_client = self.swift_fixture.connect()
        for lfc, contents in zip(self.lfcs, self.contents):
            container, name = swift.swift_location(lfc.id)
            headers, obj = swift_client.get_object(container, name)
            self.assertEqual(contents, obj, 'Did not round trip')

    def test_librarian_serves_from_swift(self):
        log = BufferLogger()

        # Move all the files into Swift and off the file system.
        swift.to_swift(log, remove=True)

        # Confirm we can still access the files from the Librarian.
        for lfa_id, content in zip(self.lfa_ids, self.contents):
            data = self.librarian_client.getFileByAlias(lfa_id).read()
            self.assertEqual(content, data)

    def test_librarian_serves_from_disk(self):
        # Ensure the Librarian falls back to serving files from disk
        # when they cannot be found in the Swift server. Note that other
        # Librarian tests do not have Swift active, so this test is not
        # redundant.
        for lfa_id, content in zip(self.lfa_ids, self.contents):
            data = self.librarian_client.getFileByAlias(lfa_id).read()
            self.assertEqual(content, data)
