# Copyright 2004 Canonical Ltd.  All rights reserved.
#

"""Tests for ftparchive.py"""

__metaclass__ = type

import os
import shutil
from StringIO import StringIO
import unittest

from zope.component import getUtility

from canonical.config import config
from canonical.archivepublisher.config import Config
from canonical.archivepublisher.pool import (
    DiskPool, Poolifier)
from canonical.archivepublisher.tests.util import (
    FakeSourcePublishing, FakeBinaryPublishing, FakeLogger)
from canonical.launchpad.ftests.harness import (
    LaunchpadZopelessTestCase, LaunchpadZopelessTestSetup)
from canonical.launchpad.interfaces import (
    ILibraryFileAliasSet, IDistributionSet)
from canonical.librarian.client import LibrarianClient


class TestFTPArchive(LaunchpadZopelessTestCase):
    dbuser = 'lucille'

    # Setup creates a pool dir...
    def setUp(self):
        LaunchpadZopelessTestCase.setUp(self)
        self.library = LibrarianClient()
        self._distribution = getUtility(IDistributionSet)['ubuntutest']
        self._config = Config(self._distribution)
        self._config.setupArchiveDirs()

        self._sampledir = os.path.join(config.root, "lib", "canonical",
                                       "archivepublisher", "tests", "apt-data")
        self._confdir = self._config.miscroot
        self._pooldir = self._config.poolroot
        self._overdir = self._config.overrideroot
        self._listdir = self._config.overrideroot
        self._logger = FakeLogger()
        self._dp = DiskPool(Poolifier(), self._pooldir, self._logger)

    def tearDown(self):
        LaunchpadZopelessTestCase.tearDown(self)
        shutil.rmtree(self._config.distroroot)

    def _verifyFile(self, filename, directory):
        fullpath = "%s/%s" % (directory, filename)
        assert os.stat(fullpath)
        text = file(fullpath).read()
        assert text
        assert text == file("%s/%s" % (self._sampledir, filename)).read()

    def _addMockFile(self, filename, content):
        """Add a mock file in Librarian.

        Returns a ILibraryFileAlias corresponding to the file uploaded.
        """
        alias_id = self.library.addFile(
            filename, len(content), StringIO(content), 'application/text')
        LaunchpadZopelessTestSetup.txn.commit()
        return getUtility(ILibraryFileAliasSet)[alias_id]

    def _getFakePubSource(self, sourcename, component, leafname,
                         section='', dr='',
                         filecontent="I do not care about sources."):
        """Return a mock source publishing record."""
        alias = self._addMockFile(leafname, filecontent)
        return FakeSourcePublishing(sourcename, component, leafname, alias,
                                    section, dr)

    def _getFakePubBinary(self, binaryname, component, filename,
                         section='', dr='', priority=0, archtag='',
                         filecontent="I do not care about binaries."):
        """Return a mock binary publishing record."""
        alias = self._addMockFile(filename, filecontent)
        return FakeBinaryPublishing(binaryname, component, filename, alias,
                                    section, dr, priority, archtag)

    def testInstantiate(self):
        """canonical.archivepublisher.FTPArchive should be instantiatable"""
        from canonical.archivepublisher.ftparchive import FTPArchiveHandler
        FTPArchiveHandler(self._logger, self._config, self._dp,
                   self._distribution, set())

    def testPublishOverrides(self):
        """canonical.archivepublisher.Publisher.publishOverrides should work"""
        from canonical.archivepublisher.ftparchive import FTPArchiveHandler
        fa = FTPArchiveHandler(self._logger, self._config, self._dp,
                        self._distribution, set())
        src = [self._getFakePubSource(
            "foo", "main", "foo.dsc", "misc", "warty")]
        bin = [self._getFakePubBinary(
            "foo", "main", "foo.deb", "misc", "warty", 10, "i386")]
        fa.publishOverrides(src, bin)
        # Check that the files exist
        self._verifyFile("override.warty.main", self._overdir)
        self._verifyFile("override.warty.main.src", self._overdir)
        self._verifyFile("override.warty.extra.main", self._overdir)

    def testPublishFileLists(self):
        """canonical.archivepublisher.Publisher.publishFileLists should work"""
        from canonical.archivepublisher.ftparchive import FTPArchiveHandler
        fa = FTPArchiveHandler(self._logger, self._config, self._dp,
                        self._distribution, set())
        src = [self._getFakePubSource(
            "foo", "main", "foo.dsc", "misc", "warty")]
        bin = [self._getFakePubBinary(
            "foo", "main", "foo.deb", "misc", "warty", 10, "i386")]
        fa.publishFileLists(src, bin)
        self._verifyFile("warty_main_source", self._listdir)
        self._verifyFile("warty_main_binary-i386", self._listdir)

    def testGenerateConfig(self):
        """Generate apt-ftparchive config"""
        from canonical.archivepublisher.ftparchive import FTPArchiveHandler
        fa = FTPArchiveHandler(self._logger, self._config, self._dp,
                        self._distribution, set())
        fa.generateConfig(fullpublish=True)
        self._verifyFile("apt.conf", self._confdir)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

