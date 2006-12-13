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

from canonical.launchpad.scripts.ftpmaster import SyncSource


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
        self.debugs = []
        self.errors = []
        self.downloads = []

    def tearDown(self):
        """Remove test contents from disk.

        chdir back to the previous path (home) and remove the temp
        directory used as jail.
        """
        os.chdir(self._home)
        cleanupLibrarianFiles()
        shutil.rmtree(self._jail)

    def _listfiles(self):
        """Return a list of files present in jail."""
        return os.listdir(self._jail)

    def local_debug(self, message):
        """ """
        self.debugs.append(message)

    def local_error(self, message):
        """ """
        self.errors.append(message)

    def local_downloader(self, url, filename):
        """ """
        self.downloads.append((url, filename))
        output = open(filename, 'w')
        output.write('Slartibartfast')
        output.close()

    def getSyncSource(self, files, origin):
        """Return a SyncSource instance with the given parameters

        Pass the helper functions.
        """
        sync_source = SyncSource(
            files=files, origin=origin, debug=self.local_debug,
            error=self.local_error, downloader=self.local_downloader)
        return sync_source

    def testInstantiate(self):
        """Check if SyncSource can be instantiated."""
        files = {'foobar': {'size': 1}}
        origin = {'foobar': {'remote-location': 'nowhere'}}

        sync_source = self.getSyncSource(files, origin)

        self.assertEqual(sync_source.files, files)
        self.assertEqual(sync_source.origin, origin)

        sync_source.debug('opa')
        self.assertEqual(self.debugs, ['opa'])

        sync_source.error('oops')
        self.assertEqual(self.errors, ['oops'])

        sync_source.downloader('somewhere', 'foo')
        self.assertEqual(self.downloads, [('somewhere', 'foo')])
        self.assertEqual(self._listfiles(), ['foo'])
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
        sync_source = self.getSyncSource(files, origin)

        test_file = open('foo', 'w')
        test_file.write('abcdefghijlmnop')
        test_file.close()

        sync_source.checkDownloadedFiles()
        self.assertEqual(self.errors, [])

    def testCheckDownloadedFilesWrongMD5(self):
        """Expect an error due the wrong MD5."""
        files = {
            'foo': {'md5sum': 'duhhhhh', 'size': 15}
            }
        origin = {}
        sync_source = self.getSyncSource(files, origin)

        test_file = open('foo', 'w')
        test_file.write('abcdefghijlmnop')
        test_file.close()

        sync_source.checkDownloadedFiles()
        self.assertEqual(
            self.errors,
            ['foo: md5sum check failed '
             '(dd21ab16f950f7ac4f9c78ef1498eee1 [actual] '
             'vs. duhhhhh [expected]).'])

    def testCheckDownloadedFilesWrongSize(self):
        """Expect an error due the wrong size."""
        files = {
            'foo': {'md5sum': 'dd21ab16f950f7ac4f9c78ef1498eee1', 'size': 10}
            }
        origin = {}
        sync_source = self.getSyncSource(files, origin)

        test_file = open('foo', 'w')
        test_file.write('abcdefghijlmnop')
        test_file.close()

        sync_source.checkDownloadedFiles()

        self.assertEqual(
            self.errors,
            ['foo: size mismatch (15 [actual] vs. 10 [expected]).'])

    def testSyncSourceClassMethod(self):
        """Probe the classmethod provided by SyncSource."""
        test_file = open('foo', 'w')
        test_file.write('abcdefghijlmnop')
        test_file.close()
        md5 = SyncSource.aptMD5Sum('foo')
        self.assertEqual(md5, 'dd21ab16f950f7ac4f9c78ef1498eee1')

    def testFetchSyncFiles(self):
        """Probe fetchSyncFiles.

        It only downloads the files not present in current path, so the
        so the test_file is skipped.
        """
        files = {
            'foo.diff.gz': {'remote filename': 'xxx'},
            'foo.dsc': {'remote filename': 'yyy'},
            'foo.orig.gz': {'remote filename': 'zzz'},
            }
        origin = {'url': 'http://somewhere/'}

        sync_source = self.getSyncSource(files, origin)

        test_file = open('foo.diff.gz', 'w')
        test_file.write('nahhh')
        test_file.close()

        dsc_filename = sync_source.fetchSyncFiles()

        self.assertEqual(dsc_filename, 'foo.dsc')

        self.assertEqual(
            self.downloads,
            [('http://somewhere/yyy', 'foo.dsc'),
             ('http://somewhere/zzz', 'foo.orig.gz')])

        for url, filename in self.downloads:
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
        sync_source = self.getSyncSource(files, origin)

        orig_filename = sync_source.fetchLibrarianFiles()

        self.assertEqual(orig_filename, 'netapplet_1.0.0.orig.tar.gz')
        self.assertEqual(self._listfiles(), ['netapplet_1.0.0.orig.tar.gz'])
        self.assertEqual(
            self.debugs,
            ['\tnetapplet_1.0.0.orig.tar.gz: already in distro '
             '- downloading from librarian'])
        self.assertEqual(self.errors, [])

    def testFetchLibrarianFilesGotDuplicatedDSC(self):
        """fetchLibrarianFiles fails for an already present version.

        It should stop via 'errorback' when it find a DSC or DIFF already
        published, it means that the upload version is duplicated.
        """
        files = {
            'foobar-1.0.orig.tar.gz': {},
            'foobar-1.0.dsc': {},
            'foobar-1.0.diff.gz': {},
            }
        origin = {}
        sync_source = self.getSyncSource(files, origin)

        orig_filename = sync_source.fetchLibrarianFiles()

        self.assertEqual(orig_filename, None)
        self.assertEqual(self._listfiles(), ['foobar-1.0.dsc'])
        self.assertEqual(
            self.debugs,
            ['\tfoobar-1.0.dsc: already in distro '
             '- downloading from librarian'])
        self.assertEqual(
            self.errors,
            ['Oops, only orig.tar.gz can be retrieved from librarian'])


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
