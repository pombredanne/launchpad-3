#!/usr/bin/env python

# Copyright 2004 Canonical Ltd.  All rights reserved.
#

import unittest
import sys
import os
import shutil

from canonical.lp.dbschema import PackagePublishingStatus
from canonical.lucille.config import Config

from canonical.lucille.tests import datadir

from canonical.lucille.tests.util import FakeDownloadClient, \
                                         FakeSourcePublishing, \
                                         FakeBinaryPublishing, \
                                         _deepCopy, dist, drs

sourceinput1 = [
    FakeSourcePublishing("foo", "main", "foo.dsc", 1)
    ]

sourceinput2 = [
    FakeSourcePublishing("foo", "main", "foo.dsc", 1, "misc", "warty")
    ]

binaryinput1 = [
    FakeBinaryPublishing("foo", "main", "foo.deb", 1)
    ]

binaryinput2 = [
    FakeBinaryPublishing("foo", "main", "foo.deb", 1,
                         "misc", "warty", 10, "i386")
    ]

cnf = Config(dist,drs)

class TestPublisher(unittest.TestCase):

    # Setup creates a pool dir...
    def setUp(self):
        for thisdir in [
            cnf.distroroot,
            cnf.archiveroot,
            cnf.poolroot,
            cnf.distsroot,
            cnf.overrideroot,
            cnf.cacheroot,
            cnf.miscroot ]:
            os.makedirs(thisdir)
        self._libr = FakeDownloadClient();
        self._pooldir = cnf.poolroot
        self._overdir = cnf.overrideroot
        self._listdir = cnf.overrideroot
        
    # Tear down blows the pool dir away...
    def tearDown(self):
        shutil.rmtree(cnf.distroroot)
    

    def testImport(self):
        """canonical.lucille.Publisher should be importable"""
        from canonical.lucille import Publisher

    def testInstantiate(self):
        """canonical.lucille.Publisher should be instantiatable"""
        from canonical.lucille import Publisher
        p = Publisher(cnf, self._libr)

    def testPathFor(self):
        """canonical.lucille.Publisher._pathfor should work"""
        from canonical.lucille import Publisher
        p = Publisher(cnf, self._libr)
        cases = (
            ("foo", "main", None, "%s/main/f/foo" % cnf.poolroot),
            ("foo", "main", "foo.deb", "%s/main/f/foo/foo.deb" % cnf.poolroot)
            )
        for case in cases:
            self.assertEqual( case[3], p._pathfor(case[0],case[1],case[2]) )

    def testPrepareDir(self):
        """canonical.lucille.Publisher._preparedir should work"""
        from canonical.lucille import Publisher
        p = Publisher(cnf, self._libr)
        p._preparedir( "foo", "main" )
        self.assertEqual( True, os.path.isdir("%s/main/f/foo" % self._pooldir))

    def testPublish(self):
        """canonical.lucille.Publisher._publish should work"""
        from canonical.lucille import Publisher
        p = Publisher(cnf, self._libr)
        p._publish( "foo", "main", "foo.txt", 1 )
        f = "%s/main/f/foo/foo.txt" % self._pooldir
        os.stat(f) # Raises if it's not there. That'll do for now

    def testFullPublishSource(self):
        """canonical.lucille.Publisher.publish should work for sources"""
        from canonical.lucille import Publisher
        p = Publisher(cnf, self._libr)
        src = _deepCopy(sourceinput1)
        p.publish( src )
        f = "%s/main/f/foo/foo.dsc" % self._pooldir
        os.stat(f)

    def testFullPublishBinary(self):
        """canonical.lucille.Publisher.publish should work for sources"""
        from canonical.lucille import Publisher
        p = Publisher(cnf, self._libr)
        bin = _deepCopy(binaryinput1)
        p.publish( bin, False )
        f = "%s/main/f/foo/foo.deb" % self._pooldir
        os.stat(f)

    def testPublishOverrides(self):
        """canonical.lucille.Publisher.publishOverrides should work"""
        from canonical.lucille import Publisher
        p = Publisher(cnf, self._libr)
        src = _deepCopy(sourceinput2)
        bin = _deepCopy(binaryinput2)
        p.publishOverrides( src, bin )
        # Check that the files exist
        os.stat("%s/override.warty.main" % self._overdir)
        os.stat("%s/override.warty.main.src" % self._overdir)

    def testPublishFileLists(self):
        """canonical.lucille.Publisher.publishFileLists should work"""
        from canonical.lucille import Publisher
        p = Publisher(cnf, self._libr)
        src = _deepCopy(sourceinput2)
        bin = _deepCopy(binaryinput2)
        p.publishFileLists( src, bin )
        os.stat("%s/warty_main_source" % self._listdir )
        os.stat("%s/warty_main_binary-i386" % self._listdir )

    def testGenerateConfig(self):
        """canonical.lucille.Publisher.generateAptFTPConfig should work"""
        from canonical.lucille import Publisher
        p = Publisher(cnf, self._libr)
        s = p.generateAptFTPConfig()
        # XXX: dsilvers 2004-11-15
        # For now, all we can sensibly do is assert that the config was created
        # In future we may parse it and check values make sense.

def test_suite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestPublisher))
    return suite

def main(argv):
    suite = test_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    if not runner.run(suite).wasSuccessful():
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

