# Copyright 2006 Canonical Ltd.  All rights reserved.
"""ChrootManager facilities tests."""

__metaclass__ = type

import os
import shutil
import tempfile
from unittest import TestCase, TestLoader

from canonical.librarian.ftests.harness import (
    fillLibrarianFile, cleanupLibrarianFiles)
from canonical.testing import LaunchpadZopelessLayer

from canonical.launchpad.scripts.ftpmaster import (
    SyncSource, SyncSourceError)


class TestSyncSource(TestCase):
    layer = LaunchpadZopelessLayer
    dbuser = 'ro'

    def setUp(self):
        """Create contents in disk for librarian sampledata.

        Setup and chdir into a temp directory, a jail, where we can
        control the file creation properly
        """
        fillLibrarianFile(1, content='one')
        fillLibrarianFile(2, content='two')
        fillLibrarianFile(54, content='fifty-four')
        self._home = os.path.abspath('')
        self._jail = tempfile.mkdtemp()
        os.chdir(self._jail)
        self.messages = []
        self.downloads = []

    def tearDown(self):
        """Remove test contents from disk.

        chdir back to the previous path (home) and remove the temp
        directory used as jail.
        """
        os.chdir(self._home)
        cleanupLibrarianFiles()
        shutil.rmtree(self._jail)

    def _listFiles(self):
        """Return a list of files present in jail."""
        return os.listdir(self._jail)

    def local_debug(self, message):
        """Store debug messages for future inspection."""
        self.messages.append(message)

    def local_downloader(self, url, filename):
        """Store download requests for future inspections."""
        self.downloads.append((url, filename))
        output = open(filename, 'w')
        output.write('Slartibartfast')
        output.close()

    def _getSyncSource(self, files, origin):
        """Return a SyncSource instance with the given parameters

        Uses the local_* methods to capture results so we can verify
        them later.
        """
        sync_source = SyncSource(
            files=files, origin=origin, debug=self.local_debug,
            downloader=self.local_downloader)
        return sync_source

    def testInstantiate(self):
        """Check if SyncSource can be instantiated."""
        files = {'foobar': {'size': 1}}
        origin = {'foobar': {'remote-location': 'nowhere'}}

        sync_source = self._getSyncSource(files, origin)

        self.assertEqual(sync_source.files, files)
        self.assertEqual(sync_source.origin, origin)

        sync_source.debug('opa')
        self.assertEqual(self.messages, ['opa'])

        sync_source.downloader('somewhere', 'foo')
        self.assertEqual(self.downloads, [('somewhere', 'foo')])
        self.assertEqual(self._listFiles(), ['foo'])
        self.assertEqual(open('foo').read(), 'Slartibartfast')

    def testCheckDownloadedFilesOK(self):
        """Check if checkDownloadFiles really verifies the filesystem

        Pass parameters via 'files' (MD5 & size) that match the file created
        on disk.
        """
        files = {
            'foo': {'md5sum': 'dd21ab16f950f7ac4f9c78ef1498eee1', 'size': 15}
            }
        origin = {}
        sync_source = self._getSyncSource(files, origin)

        test_file = open('foo', 'w')
        test_file.write('abcdefghijlmnop')
        test_file.close()

        sync_source.checkDownloadedFiles()

    def testCheckDownloadedFilesWrongMD5(self):
        """Expect SyncSourceError to be raised due the wrong MD5."""
        files = {
            'foo': {'md5sum': 'duhhhhh', 'size': 15}
            }
        origin = {}
        sync_source = self._getSyncSource(files, origin)

        test_file = open('foo', 'w')
        test_file.write('abcdefghijlmnop')
        test_file.close()

        self.assertRaises(
            SyncSourceError,
            sync_source.checkDownloadedFiles)

    def testCheckDownloadedFilesWrongSize(self):
        """Expect SyncSourceError to be raised due the wrong size."""
        files = {
            'foo': {'md5sum': 'dd21ab16f950f7ac4f9c78ef1498eee1', 'size': 10}
            }
        origin = {}
        sync_source = self._getSyncSource(files, origin)

        test_file = open('foo', 'w')
        test_file.write('abcdefghijlmnop')
        test_file.close()

        self.assertRaises(
            SyncSourceError,
            sync_source.checkDownloadedFiles)

    def testSyncSourceMD5Sum(self):
        """Probe the classmethod provided by SyncSource."""
        test_file = open('foo', 'w')
        test_file.write('abcdefghijlmnop')
        test_file.close()
        md5 = SyncSource.generateMD5Sum('foo')
        self.assertEqual(md5, 'dd21ab16f950f7ac4f9c78ef1498eee1')

    def testFetchSyncFiles(self):
        """Probe fetchSyncFiles.

        It only downloads the files not present in current path, so the
        test_file is skipped.
        """
        files = {
            'foo.diff.gz': {'remote filename': 'xxx'},
            'foo.dsc': {'remote filename': 'yyy'},
            'foo.orig.gz': {'remote filename': 'zzz'},
            }
        origin = {'url': 'http://somewhere/'}

        sync_source = self._getSyncSource(files, origin)

        test_file = open('foo.diff.gz', 'w')
        test_file.write('nahhh')
        test_file.close()

        dsc_filename = sync_source.fetchSyncFiles()

        self.assertEqual(dsc_filename, 'foo.dsc')

        self.assertEqual(
            self.downloads,
            [('http://somewhere/yyy', 'foo.dsc'),
             ('http://somewhere/zzz', 'foo.orig.gz')])

        for filename in files.keys():
            self.assertTrue(os.path.exists(filename))

    def testFetchLibrarianFilesOK(self):
        """Probe fetchLibrarianFiles.

        Seek on files published from librarian and download matching filenames.
        """
        files = {
            'netapplet_1.0.0.orig.tar.gz': {},
            'netapplet_1.0.1.dsc': {},
            'netapplet_1.0.1.diff.gz': {},
            }
        origin = {}
        sync_source = self._getSyncSource(files, origin)

        orig_filename = sync_source.fetchLibrarianFiles()

        self.assertEqual(orig_filename, 'netapplet_1.0.0.orig.tar.gz')
        self.assertEqual(self._listFiles(), ['netapplet_1.0.0.orig.tar.gz'])
        self.assertEqual(
            self.messages,
            ['\tnetapplet_1.0.0.orig.tar.gz: already in distro '
             '- downloading from librarian'])

    def testFetchLibrarianFilesGotDuplicatedDSC(self):
        """fetchLibrarianFiles fails for an already present version.

        It raises SyncSourceError when it find a DSC or DIFF already
        published, it means that the upload version is duplicated.
        """
        files = {
            'foobar-1.0.orig.tar.gz': {},
            'foobar-1.0.dsc': {},
            'foobar-1.0.diff.gz': {},
            }
        origin = {}
        sync_source = self._getSyncSource(files, origin)

        self.assertRaises(
            SyncSourceError,
            sync_source.fetchLibrarianFiles)

        self.assertEqual(
            self.messages,
            ['\tfoobar-1.0.dsc: already in distro '
             '- downloading from librarian'])
        self.assertEqual(self._listFiles(), ['foobar-1.0.dsc'])


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
