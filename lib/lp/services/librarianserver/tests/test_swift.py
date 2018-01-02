# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Librarian disk to Swift storage tests."""

__metaclass__ = type

from cStringIO import StringIO
import hashlib
import os.path
import time

from mock import patch
from swiftclient import client as swiftclient
import transaction

from lp.services.database import write_transaction
from lp.services.database.interfaces import IStore
from lp.services.features.testing import FeatureFixture
from lp.services.librarian.client import LibrarianClient
from lp.services.librarian.model import LibraryFileAlias
from lp.services.librarianserver.storage import LibrarianStorage
from lp.services.log.logger import BufferLogger
from lp.testing import TestCase
from lp.testing.layers import BaseLayer, LaunchpadZopelessLayer, LibrarianLayer
from lp.testing.swift.fixture import SwiftFixture

from lp.services.librarianserver import swift


class TestFeedSwift(TestCase):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestFeedSwift, self).setUp()
        self.swift_fixture = self.useFixture(SwiftFixture())
        self.useFixture(FeatureFixture({'librarian.swift.enabled': True}))
        transaction.commit()

        self.addCleanup(swift.connection_pool.clear)

        # Restart the Librarian so it picks up the OS_* environment
        # variables.
        LibrarianLayer.librarian_fixture.killTac()
        LibrarianLayer.librarian_fixture.setUp()

        # Add some files. These common sample files all have their
        # modification times set to the past so they will not be
        # considered potential in-progress uploads.
        the_past = time.time() - 25 * 60 * 60
        self.librarian_client = LibrarianClient()
        self.contents = [str(i) * i for i in range(1, 5)]
        self.lfa_ids = [
            self.add_file('file_{0}'.format(i), content, when=the_past)
            for content in self.contents]
        self.lfas = [
            IStore(LibraryFileAlias).get(LibraryFileAlias, lfa_id)
                for lfa_id in self.lfa_ids]
        self.lfcs = [lfa.content for lfa in self.lfas]

    def tearDown(self):
        super(TestFeedSwift, self).tearDown()
        # Restart the Librarian so it picks up the feature flag change.
        LibrarianLayer.librarian_fixture.killTac()
        LibrarianLayer.librarian_fixture.setUp()

    @write_transaction
    def add_file(self, name, content, when=None, content_type='text/plain'):
        lfa_id = self.librarian_client.addFile(
            name=name, size=len(content), file=StringIO(content),
            contentType=content_type)
        if when is None:
            when = 0  # Very very old
        lfa = IStore(LibraryFileAlias).get(LibraryFileAlias, lfa_id)
        path = swift.filesystem_path(lfa.content.id)
        os.utime(path, (when, when))
        return lfa_id

    def test_copy_to_swift(self):
        log = BufferLogger()

        # Confirm that files exist on disk where we expect to find them.
        for lfc in self.lfcs:
            path = swift.filesystem_path(lfc.id)
            self.assertTrue(os.path.exists(path))

        # Copy all the files into Swift.
        swift.to_swift(log, remove_func=None)

        # Confirm that files exist on disk where we expect to find them.
        for lfc in self.lfcs:
            path = swift.filesystem_path(lfc.id)
            self.assertTrue(os.path.exists(path))

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
            swift.to_swift(log)  # remove_func == None

    def test_copy_to_swift_and_rename(self):
        log = BufferLogger()

        # Confirm that files exist on disk where we expect to find them.
        for lfc in self.lfcs:
            path = swift.filesystem_path(lfc.id)
            self.assertTrue(os.path.exists(path))

        # Copy all the files into Swift.
        swift.to_swift(log, remove_func=swift.rename)

        # Confirm that files exist on disk where we expect to find them.
        for lfc in self.lfcs:
            path = swift.filesystem_path(lfc.id) + '.migrated'
            self.assertTrue(os.path.exists(path))

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
            swift.to_swift(log, remove_func=swift.rename)  # remove == False

    def test_move_to_swift(self):
        log = BufferLogger()

        # Confirm that files exist on disk where we expect to find them.
        for lfc in self.lfcs:
            path = swift.filesystem_path(lfc.id)
            self.assertTrue(os.path.exists(path))

        # Migrate all the files into Swift.
        swift.to_swift(log, remove_func=os.unlink)

        # Confirm that all the files have gone from disk.
        for lfc in self.lfcs:
            self.assertFalse(os.path.exists(swift.filesystem_path(lfc.id)))

        # Confirm all the files are in Swift.
        swift_client = self.swift_fixture.connect()
        for lfc, contents in zip(self.lfcs, self.contents):
            container, name = swift.swift_location(lfc.id)
            headers, obj = swift_client.get_object(container, name)
            self.assertEqual(contents, obj, 'Did not round trip')

    def test_librarian_serves_from_swift(self):
        log = BufferLogger()

        # Move all the files into Swift and off the file system.
        swift.to_swift(log, remove_func=os.unlink)

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

    def test_largish_binary_files_from_disk(self):
        # Generate a largish blob, including null bytes for kicks.
        # A largish file is large enough that the HTTP upload needs
        # to be done in multiple chunks, but small enough that it is
        # stored in Swift as a single object.
        size = 512 * 1024  # 512KB
        expected_content = ''.join(chr(i % 256) for i in range(0, size))
        lfa_id = self.add_file('hello_bigboy.xls', expected_content)

        # Data round trips when served from disk.
        lfa = self.librarian_client.getFileByAlias(lfa_id)
        self.assertEqual(expected_content, lfa.read())

    def test_largish_binary_files_from_swift(self):
        # Generate large blob, multiple of the chunk size.
        # Including null bytes for kicks.
        # A largish file is large enough that the HTTP upload needs
        # to be done in multiple chunks, but small enough that it is
        # stored in Swift as a single object.
        size = LibrarianStorage.CHUNK_SIZE * 50
        self.assertTrue(size > 1024 * 1024)
        expected_content = ''.join(chr(i % 256) for i in range(0, size))
        lfa_id = self.add_file('hello_bigboy.xls', expected_content)
        lfc = IStore(LibraryFileAlias).get(LibraryFileAlias, lfa_id).content

        # This data size is a multiple of our chunk size.
        self.assertEqual(
            0, len(expected_content) % LibrarianStorage.CHUNK_SIZE)

        # Data round trips when served from Swift.
        swift.to_swift(BufferLogger(), remove_func=os.unlink)
        self.assertFalse(os.path.exists(swift.filesystem_path(lfc.id)))
        lfa = self.librarian_client.getFileByAlias(lfa_id)
        self.assertEqual(expected_content, lfa.read())

    def test_largish_binary_files_from_swift_offset(self):
        # Generate large blob, but NOT a multiple of the chunk size.
        # Including null bytes for kicks.
        # A largish file is large enough that the HTTP upload needs
        # to be done in multiple chunks, but small enough that it is
        # stored in Swift as a single object.
        size = LibrarianStorage.CHUNK_SIZE * 50 + 1
        self.assertTrue(size > 1024 * 1024)
        expected_content = ''.join(chr(i % 256) for i in range(0, size))
        lfa_id = self.add_file('hello_bigboy.xls', expected_content)
        lfc = IStore(LibraryFileAlias).get(LibraryFileAlias, lfa_id).content

        # This data size is NOT a multiple of our chunk size.
        self.assertNotEqual(
            0, len(expected_content) % LibrarianStorage.CHUNK_SIZE)

        # Data round trips when served from Swift.
        swift.to_swift(BufferLogger(), remove_func=os.unlink)
        lfa = self.librarian_client.getFileByAlias(lfa_id)
        self.assertFalse(os.path.exists(swift.filesystem_path(lfc.id)))
        self.assertEqual(expected_content, lfa.read())

    def test_large_file_to_swift(self):
        # Generate a blob large enough that Swift requires us to store
        # it as multiple objects plus a manifest.
        size = LibrarianStorage.CHUNK_SIZE * 50
        self.assertTrue(size > 1024 * 1024)
        expected_content = ''.join(chr(i % 256) for i in range(0, size))
        lfa_id = self.add_file('hello_bigboy.xls', expected_content)
        lfa = IStore(LibraryFileAlias).get(LibraryFileAlias, lfa_id)
        lfc = lfa.content

        # We don't really want to upload a file >5GB to our mock Swift,
        # so change the constant instead. Set it so we need 3 segments.
        def _reset_max(val):
            swift.MAX_SWIFT_OBJECT_SIZE = val
        self.addCleanup(_reset_max, swift.MAX_SWIFT_OBJECT_SIZE)
        swift.MAX_SWIFT_OBJECT_SIZE = int(size / 2) - 1

        # Shove the file requiring multiple segments into Swift.
        swift.to_swift(BufferLogger(), remove_func=None)

        # As our mock Swift does not support multi-segment files,
        # instead we examine it directly in Swift as best we can.
        swift_client = self.swift_fixture.connect()

        # The manifest exists. Unfortunately, we can't test that the
        # magic manifest header is set correctly.
        container, name = swift.swift_location(lfc.id)
        headers, obj = swift_client.get_object(container, name)
        self.assertEqual(obj, '')

        # The segments we expect are all in their expected locations.
        _, obj1 = swift_client.get_object(container, '{0}/0000'.format(name))
        _, obj2 = swift_client.get_object(container, '{0}/0001'.format(name))
        _, obj3 = swift_client.get_object(container, '{0}/0002'.format(name))
        self.assertRaises(
            swiftclient.ClientException, swift_client.get_object,
            container, '{0}/0003'.format(name))

        # Our object round tripped
        self.assertEqual(obj1 + obj2 + obj3, expected_content)


class TestHashStream(TestCase):
    layer = BaseLayer

    def test_read(self):
        empty_md5 = 'd41d8cd98f00b204e9800998ecf8427e'
        s = swift.HashStream(StringIO('make me a coffee'))
        self.assertEqual(s.hash.hexdigest(), empty_md5)
        data = s.read()
        self.assertEqual(data, 'make me a coffee')
        self.assertEqual(s.hash.hexdigest(),
                         '17dfd3e9f99a2260552e898406c696e9')

    def test_partial_read(self):
        empty_sha1 = 'da39a3ee5e6b4b0d3255bfef95601890afd80709'
        s = swift.HashStream(StringIO('make me another coffee'), hashlib.sha1)
        self.assertEqual(s.hash.hexdigest(), empty_sha1)
        chunk = s.read(4)
        self.assertEqual(chunk, 'make')
        self.assertEqual(s.hash.hexdigest(),
                         '5821eb27d7b71c9078000da31a5a654c97e401b9')
        chunk = s.read()
        self.assertEqual(chunk, ' me another coffee')
        self.assertEqual(s.hash.hexdigest(),
                         '8c826e573016ce05f3968044f82507b46fd2aa93')

    def test_tell(self):
        s = swift.HashStream(StringIO('hurry up with that coffee'))
        self.assertEqual(s.tell(), 0)
        s.read(4)
        self.assertEqual(s.tell(), 4)

    def test_seek(self):
        s = swift.HashStream(StringIO('hurry up with that coffee'))
        s.seek(0)
        self.assertEqual(s.tell(), 0)
        s.seek(6)
        self.assertEqual(s.tell(), 6)
        chunk = s.read()
        self.assertEqual(chunk, 'up with that coffee')
        self.assertEqual(s.hash.hexdigest(),
                         '0687b12af46824e3584530c5262fed36')

        # Seek also must reset the hash.
        s.seek(2)
        chunk = s.read(3)
        self.assertEqual(chunk, 'rry')
        self.assertEqual(s.hash.hexdigest(),
                         '35cd51ccd493b67542201d20b6ed7db9')
