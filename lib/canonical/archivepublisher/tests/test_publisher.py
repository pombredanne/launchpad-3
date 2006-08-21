# Copyright 2004 Canonical Ltd.  All rights reserved.
#

"""Tests for publishing.py"""

__metaclass__ = type

import os
import sys
import shutil
from StringIO import StringIO
import unittest

from zope.component import getUtility

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


class TestPublisher(LaunchpadZopelessTestCase):
    dbuser = 'lucille'

    # Setup creates a pool dir...
    def setUp(self):
        LaunchpadZopelessTestCase.setUp(self)
        self.library = LibrarianClient()
        self._distribution = getUtility(IDistributionSet)['ubuntutest']
        self._config = Config(self._distribution)
        self._config.setupArchiveDirs()

        self._pooldir = self._config.poolroot
        self._overdir = self._config.overrideroot
        self._listdir = self._config.overrideroot
        self._logger = FakeLogger()
        self._dp = DiskPool(Poolifier(), self._pooldir, self._logger)

    def addMockFile(self, filename, content):
        """Add a mock file in Librarian.

        Returns a ILibraryFileAlias corresponding to the file uploaded.
        """
        alias_id = self.library.addFile(
            filename, len(content), StringIO(content), 'application/text')
        LaunchpadZopelessTestSetup.txn.commit()
        return getUtility(ILibraryFileAliasSet)[alias_id]

    def getFakePubSource(self, sourcename, component, leafname,
                         section='', dr='',
                         filecontent="I do not care about sources."):
        """Return a mock source publishing record."""
        alias = self.addMockFile(leafname, filecontent)
        return FakeSourcePublishing(sourcename, component, leafname, alias,
                                    section, dr)

    def getFakePubBinary(self, binaryname, component, filename,
                         section='', dr='', priority=0, archtag='',
                         filecontent="I do not care about binaries."):
        """Return a mock binary publishing record."""
        alias = self.addMockFile(filename, filecontent)
        return FakeBinaryPublishing(binaryname, component, filename, alias,
                                    section, dr, priority, archtag)

    # Tear down blows the pool dir away...
    def tearDown(self):
        LaunchpadZopelessTestCase.tearDown(self)
        shutil.rmtree(self._config.distroroot)

    def testInstantiate(self):
        """canonical.archivepublisher.Publisher should be instantiatable"""
        from canonical.archivepublisher import Publisher
        Publisher(self._logger, self._config, self._dp, self._distribution)

    def testPathFor(self):
        """canonical.archivepublisher.Publisher._pathfor should work"""
        from canonical.archivepublisher import Publisher
        p = Publisher(self._logger, self._config, self._dp, self._distribution)
        cases = (
            ("main", "foo", None, "%s/main/f/foo" % self._config.poolroot),
            ("main", "foo", "foo.deb", "%s/main/f/foo/foo.deb"
             % self._config.poolroot)
            )
        for case in cases:
            self.assertEqual( case[3], p._pathfor(case[0], case[1], case[2]) )

    def testPublishOverrides(self):
        """canonical.archivepublisher.Publisher.publishOverrides should work"""
        from canonical.archivepublisher import Publisher
        p = Publisher(self._logger, self._config, self._dp, self._distribution)
        src = [self.getFakePubSource(
            "foo", "main", "foo.dsc", "misc", "warty")]
        bin = [self.getFakePubBinary(
            "foo", "main", "foo.deb", "misc", "warty", 10, "i386")]
        p.publishOverrides(src, bin)
        # Check that the files exist
        os.stat("%s/override.warty.main" % self._overdir)
        os.stat("%s/override.warty.main.src" % self._overdir)

    def testPublishFileLists(self):
        """canonical.archivepublisher.Publisher.publishFileLists should work"""
        from canonical.archivepublisher import Publisher
        p = Publisher(self._logger, self._config, self._dp, self._distribution)
        src = [self.getFakePubSource(
            "foo", "main", "foo.dsc", "misc", "warty")]
        bin = [self.getFakePubBinary(
            "foo", "main", "foo.deb", "misc", "warty", 10, "i386")]
        p.publishFileLists(src, bin)
        os.stat("%s/warty_main_source" % self._listdir)
        os.stat("%s/warty_main_binary-i386" % self._listdir)

    def testGenerateConfig(self):
        """Generate apt-ftparchive config"""
        from canonical.archivepublisher import Publisher
        p = Publisher(self._logger, self._config, self._dp, self._distribution)
        p.generateAptFTPConfig()
        # XXX: dsilvers 2004-11-15
        # For now, all we can sensibly do is assert that the config was created
        # In future we may parse it and check values make sense.


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
