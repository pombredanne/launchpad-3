# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for `ExportFileStorage`."""

__metaclass__ = type

from cStringIO import StringIO
from tarfile import TarFile
import unittest

from canonical.launchpad.translationformat import ExportFileStorage
from canonical.testing import LaunchpadZopelessLayer


class ExportFileStorageTestCase(unittest.TestCase):
    """Test class for translation importer component."""
    layer = LaunchpadZopelessLayer

    def testEmpty(self):
        """Behaviour of empty storage."""
        storage = ExportFileStorage('application/x-po')
        # Try not inserting any files, so the storage object remains empty.
        self.assertTrue(storage._store.isEmpty())
        self.assertFalse(storage._store.isFull())
        # Can't export an empty storage.
        self.assertRaises(AssertionError, storage.export)

    def testFull(self):
        """Behaviour of isFull."""
        storage = ExportFileStorage('application/x-po')
        storage.addFile('/tmp/a/test/file.po', 'po', 'test file')
        # The storage object starts out with a SingleFileStorageStrategy, so
        # it's full now that we've added one file.
        self.assertTrue(storage._store.isFull())
        # If we add another file however, the storage object transparently
        # switches to a TarballFileStorageStrategy.  That type of storage
        # object is never full.
        storage.addFile('/tmp/another/test/file.po', 'po', 'test file two')
        self.assertFalse(storage._store.isFull())
        # We can now add any number of files without filling the storage
        # object.
        storage.addFile('/tmp/yet/another/test/file.po', 'po', 'test file 3')
        self.assertFalse(storage._store.isFull())

    def testSingle(self):
        """Test export of single file."""
        storage = ExportFileStorage('application/x-po')
        storage.addFile('/tmp/a/test/file.po', 'po', 'test file')
        outfile = storage.export()
        self.assertEquals(outfile.path, '/tmp/a/test/file.po')
        self.assertEquals(outfile.file_extension, 'po')
        self.assertEquals(outfile.read(), 'test file')

    def testTarball(self):
        """Test export of tarball."""
        storage = ExportFileStorage('application/x-po')
        storage.addFile('/tmp/a/test/file.po', 'po', 'test file')
        storage.addFile('/tmp/another/test.po', 'po', 'another test file')
        outfile = storage.export()
        tarball = TarFile.open(mode='r|gz', fileobj=StringIO(outfile.read()))
        elements = set(tarball.getnames())
        self.assertTrue('/tmp/a/test/file.po' in elements)
        self.assertTrue('/tmp/another/test.po' in elements)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ExportFileStorageTestCase))
    return suite

