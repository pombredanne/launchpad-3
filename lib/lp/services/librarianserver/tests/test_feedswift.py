# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Librarian disk to Swift storage tests."""

__metaclass__ = type

from cStringIO import StringIO
import os.path

from lp.services.database.interfaces import IStore
from lp.services.librarian.client import LibrarianClient
from lp.services.librarian.model import LibraryFileAlias
from lp.services.log.logger import BufferLogger
from lp.testing import TestCase
from lp.testing.layers import LaunchpadZopelessLayer, LibrarianLayer
from lp.testing.swift.fixture import SwiftFixture

from lp.services.librarianserver import feedswift


class TestFeedSwift(TestCase):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestFeedSwift, self).setUp()
        self.swift_fixture = self.useFixture(SwiftFixture())

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

    def test_to_swift(self):
        log = BufferLogger()

        # Confirm that files exist on disk where we expect to find them.
        for lfc in self.lfcs:
            path = feedswift.filesystem_path(lfc.id)
            self.assert_(os.path.exists(path))

        # Migrate all the files into Swift.
        feedswift.to_swift(log, remove=True)

        # Confirm that all the files have gone from disk.
        for lfc in self.lfcs:
            self.failIf(os.path.exists(feedswift.filesystem_path(lfc.id)))

        # Confirm all the files are in Swift.
        swift = self.swift_fixture.connect()
        for lfc, contents in zip(self.lfcs, self.contents):
            container, name = feedswift.swift_location(lfc.id)
            headers, obj = swift.get_object(container, name)
            self.assertEqual(contents, obj, 'Did not round trip')
