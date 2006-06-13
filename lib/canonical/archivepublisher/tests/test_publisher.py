#!/usr/bin/env python

# Copyright 2004 Canonical Ltd.  All rights reserved.
#

import unittest
import sys
import os
import shutil
from StringIO import StringIO

from zope.component import getUtility

from canonical.functional import ZopelessLayer
from canonical.launchpad.ftests.harness import (
    LaunchpadZopelessTestCase, LaunchpadZopelessTestSetup)
from canonical.launchpad.interfaces import ILibraryFileAliasSet

from canonical.librarian.ftests.harness import LibrarianTestSetup
from canonical.librarian.client import LibrarianClient

from canonical.archivepublisher.config import Config
from canonical.archivepublisher.pool import (
    DiskPool, Poolifier)
from canonical.archivepublisher.tests.util import (
    FakeSourcePublishing, FakeBinaryPublishing, FakeLogger, dist, drs)
from canonical.lp.dbschema import PackagePublishingStatus


cnf = Config(dist, drs)

class TestPublisher(LaunchpadZopelessTestCase):
    layer = ZopelessLayer
    dbuser = 'lucille'

    # Setup creates a pool dir...
    def setUp(self):
        LaunchpadZopelessTestCase.setUp(self)
        self.library = LibrarianClient()
        self._pooldir = cnf.poolroot
        self._overdir = cnf.overrideroot
        self._listdir = cnf.overrideroot
        self._logger = FakeLogger()
        self._dp = DiskPool(Poolifier(), self._pooldir, self._logger)
        self.setupTestPool()
        self.librarian = LibrarianTestSetup()
        self.librarian.setUp()

    def setupTestPool(self):
        """Create the required directories in test pool location."""
        required_dirs = [
            cnf.distroroot,
            cnf.archiveroot,
            cnf.poolroot,
            cnf.distsroot,
            cnf.overrideroot,
            cnf.cacheroot,
            cnf.miscroot
            ]
        for thisdir in required_dirs:
            os.makedirs(thisdir)

    def addMockFile(self, filename, content):
        """Add a mock file in Librarian.

        Returns a ILibraryFileAlias corresponding to the file uploaded.
        """
        alias_id = self.library.addFile(
            filename, len(content), StringIO(content), 'application/text')
        LaunchpadZopelessTestSetup.txn.commit()
        return getUtility(ILibraryFileAliasSet)[alias_id]

    def getMockPubSource(self, sourcename, component, leafname,
                         section='', dr='',
                         filecontent="I do not care about sources."):
        """Return a mock source publishing record."""
        alias = self.addMockFile(leafname, filecontent)
        return FakeSourcePublishing(sourcename, component, leafname, alias,
                                    section, dr)

    def getMockPubBinary(self, sourcename, component, leafname,
                         section='', dr='', priority=0, archtag='',
                         filecontent="I do not care about binaries."):
        """Return a mock binary publishing record."""
        alias = self.addMockFile(leafname, filecontent)
        return FakeBinaryPublishing(sourcename, component, leafname, alias,
                                    section, dr, priority, archtag)

    # Tear down blows the pool dir away...
    def tearDown(self):
        self.librarian.tearDown()
        LaunchpadZopelessTestCase.tearDown(self)
        shutil.rmtree(cnf.distroroot)

    def testInstantiate(self):
        """canonical.archivepublisher.Publisher should be instantiatable"""
        from canonical.archivepublisher import Publisher
        Publisher(self._logger, cnf, self._dp, dist,)

    def testPathFor(self):
        """canonical.archivepublisher.Publisher._pathfor should work"""
        from canonical.archivepublisher import Publisher
        p = Publisher(self._logger, cnf, self._dp, dist)
        cases = (
            ("main", "foo", None, "%s/main/f/foo" % cnf.poolroot),
            ("main", "foo", "foo.deb", "%s/main/f/foo/foo.deb" % cnf.poolroot)
            )
        for case in cases:
            self.assertEqual( case[3], p._pathfor(case[0], case[1], case[2]) )

    def testPublish(self):
        """Test publishOne in normal conditions (new file)."""
        from canonical.archivepublisher import Publisher
        p = Publisher(self._logger, cnf, self._dp, dist)
        pub_source = self.getMockPubSource( "foo", "main", "foo.txt",
                                            filecontent='Hello world')
        p.publishOne(pub_source)
        self.assertEqual(pub_source.sourcepackagepublishing.status,
                         PackagePublishingStatus.PUBLISHED)
        foo_name = "%s/main/f/foo/foo.txt" % self._pooldir
        self.assertEqual(open(foo_name).read().strip(), 'Hello world')

    def testPublishingOverwriteFileInPool(self):
        """Test if publishOne refuses to overwrite a file in pool.

        Check if it also keeps the original file content.
        """
        from canonical.archivepublisher import Publisher

        # publish 'foo' by-hand and ensure it has a special content
        foo_name = "%s/main/f/foo/foo.txt" % self._pooldir
        os.mkdir(os.path.join(self._pooldir, 'main'))
        os.mkdir(os.path.join(self._pooldir, 'main', 'f'))
        os.mkdir(os.path.join(self._pooldir, 'main', 'f', 'foo'))
        open(foo_name, 'w').write('Hello world')

        # try to publish 'foo' again, via publisher, and check the content
        self._dp.scan()
        p = Publisher(self._logger, cnf, self._dp, dist)
        pub_source = self.getMockPubSource("foo", "main", "foo.txt",
                                           filecontent="Something")
        p.publishOne(pub_source)
        self.assertEqual(pub_source.sourcepackagepublishing.status,
                         PackagePublishingStatus.PENDING)
        self.assertEqual(open(foo_name).read().strip(), 'Hello world')

    def testPublishingDiferentContents(self):
        """Test if publishOne refuses to overwrite its own publication."""
        from canonical.archivepublisher import Publisher

        p = Publisher(self._logger, cnf, self._dp, dist)
        pub_source = self.getMockPubSource("foo", "main", "foo.txt",
                                           filecontent='foo is happy')
        p.publishOne(pub_source)

        foo_name = "%s/main/f/foo/foo.txt" % self._pooldir
        self.assertEqual(pub_source.sourcepackagepublishing.status,
                         PackagePublishingStatus.PUBLISHED)
        self.assertEqual(open(foo_name).read().strip(), 'foo is happy')

        # try to publish 'foo' again with a different content, it
        # raises and keep the files with the original content.
        pub_source2 = self.getMockPubSource("foo", "main", "foo.txt",
                                            'foo is depressing')
        p.publishOne(pub_source2)
        self.assertEqual(pub_source2.sourcepackagepublishing.status,
                         PackagePublishingStatus.PENDING)
        self.assertEqual(open(foo_name).read().strip(), 'foo is happy')

    def testPublishingAlreadyInPool(self):
        """Test if publishOne works if file is already in Pool.

        It should identify that the file has the same content and
        mark it as PUBLISHED.
        """
        from canonical.archivepublisher import Publisher

        p = Publisher(self._logger, cnf, self._dp, dist)
        pub_source = self.getMockPubSource("bar", "main", "bar.txt",
                                           filecontent='bar is good')
        p.publishOne(pub_source)
        bar_name = "%s/main/b/bar/bar.txt" % self._pooldir
        self.assertEqual(open(bar_name).read().strip(), 'bar is good')
        self.assertEqual(pub_source.sourcepackagepublishing.status,
                         PackagePublishingStatus.PUBLISHED)

        pub_source2 = self.getMockPubSource("bar", "main", "bar.txt",
                                            filecontent='bar is good')
        p.publishOne(pub_source2)
        self.assertEqual(pub_source2.sourcepackagepublishing.status,
                         PackagePublishingStatus.PUBLISHED)

    def testPublishingSymlink(self):
        """Test if publishOne moving publication between components.

        After check if the pool file contents as the same, it should
        create a symlink in the new pointing to the original file.
        """
        from canonical.archivepublisher import Publisher

        content = 'am I a file or a symbolic link ?'
        # publish sim.txt in main and re-publish in universe
        p = Publisher(self._logger, cnf, self._dp, dist)
        pub_source = self.getMockPubSource( "sim", "main", "sim.txt",
                                            filecontent=content)
        pub_source2 = self.getMockPubSource( "sim", "universe", "sim.txt",
                                            filecontent=content)
        p.publishOne(pub_source)
        p.publishOne(pub_source2)
        self.assertEqual(pub_source.sourcepackagepublishing.status,
                         PackagePublishingStatus.PUBLISHED)
        self.assertEqual(pub_source2.sourcepackagepublishing.status,
                         PackagePublishingStatus.PUBLISHED)

        # check the resulted symbolic link
        sim_universe = "%s/universe/s/sim/sim.txt" % self._pooldir
        self.assertEqual(os.readlink(sim_universe),
                         '../../../main/s/sim/sim.txt')

        # if the contests don't match it raises.
        pub_source3 = self.getMockPubSource("sim", "restricted", "sim.txt",
                                            filecontent='It is all my fault')
        p.publishOne(pub_source3)
        self.assertEqual(pub_source3.sourcepackagepublishing.status,
                         PackagePublishingStatus.PENDING)

    def testZFullPublishSource(self):
        """Publishing a single sources"""
        from canonical.archivepublisher import Publisher
        p = Publisher(self._logger, cnf, self._dp, dist)
        src = [self.getMockPubSource("foo", "main", "foo.dsc")]
        p.publish(src)
        f = "%s/main/f/foo/foo.dsc" % self._pooldir
        os.stat(f)

    def testZFullPublishBinary(self):
        """Publishing a single binary"""
        from canonical.archivepublisher import Publisher
        p = Publisher(self._logger, cnf, self._dp, dist)
        bin = [self.getMockPubBinary("foo", "main", "foo.deb")]
        p.publish(bin, False)
        f = "%s/main/f/foo/foo.deb" % self._pooldir
        os.stat(f)

    def testPublishOverrides(self):
        """canonical.archivepublisher.Publisher.publishOverrides should work"""
        from canonical.archivepublisher import Publisher
        p = Publisher(self._logger, cnf, self._dp, dist)
        src = [self.getMockPubSource(
            "foo", "main", "foo.dsc", "misc", "warty")]
        bin = [self.getMockPubBinary(
            "foo", "main", "foo.deb", "misc", "warty", 10, "i386")]
        p.publishOverrides(src, bin)
        # Check that the files exist
        os.stat("%s/override.warty.main" % self._overdir)
        os.stat("%s/override.warty.main.src" % self._overdir)

    def testPublishFileLists(self):
        """canonical.archivepublisher.Publisher.publishFileLists should work"""
        from canonical.archivepublisher import Publisher
        p = Publisher(self._logger, cnf, self._dp, dist)
        src = [self.getMockPubSource(
            "foo", "main", "foo.dsc", "misc", "warty")]
        bin = [self.getMockPubBinary(
            "foo", "main", "foo.deb", "misc", "warty", 10, "i386")]
        p.publishFileLists(src, bin)
        os.stat("%s/warty_main_source" % self._listdir)
        os.stat("%s/warty_main_binary-i386" % self._listdir)

    def testGenerateConfig(self):
        """Generate apt-ftparchive config"""
        from canonical.archivepublisher import Publisher
        p = Publisher(self._logger, cnf, self._dp, dist)
        p.generateAptFTPConfig()
        # XXX: dsilvers 2004-11-15
        # For now, all we can sensibly do is assert that the config was created
        # In future we may parse it and check values make sense.

def test_suite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestPublisher))
    return suite

def main():
    suite = test_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    if not runner.run(suite).wasSuccessful():
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())

