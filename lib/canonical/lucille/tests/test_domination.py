#!/usr/bin/env python

# Copyright 2004 Canonical Ltd.  All rights reserved.
#

import unittest
import sys
import os
import shutil

from canonical.lp.dbschema import PackagePublishingStatus

from canonical.lucille.tests.util import FakeSource, FakeBinary, _deepCopy, \
                                         FakeDistroRelease

sourceinput1 = {
    "foo": [ FakeSource("1.0-2", PackagePublishingStatus.PUBLISHED),
             FakeSource("1.0-1", PackagePublishingStatus.PUBLISHED)
             ]
    }

binaryinput1 = {
    "foo": [ FakeBinary("1.0-2", PackagePublishingStatus.PUBLISHED),
             FakeBinary("1.0-1", PackagePublishingStatus.PUBLISHED)
             ]
    }

drc = object() # sentinel for now

class TestDominator(unittest.TestCase):

    def testImport(self):
        """canonical.lucille.Dominator should be importable"""
        from canonical.lucille import Dominator

    def testInstantiate(self):
        """canonical.lucille.Dominator should instantiate"""
        from canonical.lucille import Dominator
        d = Dominator(drc)

    def testBasicSourceDominate(self):
        """canonical.lucille.Dominator should correctly dominate source"""
        from canonical.lucille import Dominator
        d = Dominator(drc)
        src = _deepCopy(sourceinput1)
        d._dominateSource(src)
        self.assertEqual( src["foo"][0].status,
                          PackagePublishingStatus.PUBLISHED );
        self.assertEqual( src["foo"][1].status,
                          PackagePublishingStatus.SUPERCEDED );

    def testBasicBinaryDominate(self):
        """canonical.lucille.Dominator should correctly dominate binaries"""
        from canonical.lucille import Dominator
        d = Dominator(drc)
        bin = _deepCopy(binaryinput1)
        d._dominateBinary(bin)
        self.assertEqual( bin["foo"][0].status,
                          PackagePublishingStatus.PUBLISHED );
        self.assertEqual( bin["foo"][1].status,
                          PackagePublishingStatus.SUPERCEDED );

    def testSortSourcePackages(self):
        """canonical.lucille.Dominator should correctly sort sources"""
        from canonical.lucille import Dominator
        d = Dominator(drc)
        plist = [
            FakeSource('1.0-1',0,'foo'),
            FakeSource('1.0-2',0,'foo'),
            FakeSource('1.0-1',0,'bar')
            ]
        out = d._sortPackages(plist)
        self.assertEqual( len(out['foo']), 2 )
        self.assertEqual( len(out['bar']), 1 )
        self.assertEqual( out['foo'][0].version, "1.0-2" )

    def testSortBinaryPackages(self):
        """canonical.lucille.Dominator should correctly sort binaries"""
        from canonical.lucille import Dominator
        d = Dominator(drc)
        plist = [
            FakeBinary('1.0-1',0,'foo'),
            FakeBinary('1.0-2',0,'foo'),
            FakeBinary('1.0-1',0,'bar')
            ]
        out = d._sortPackages(plist, False)
        self.assertEqual( len(out['foo']), 2 )
        self.assertEqual( len(out['bar']), 1 )
        self.assertEqual( out['foo'][0].version, "1.0-2" )

    def testDomination(self):
        """canonical.lucille.Dominator should dominate properly"""
        from canonical.lucille import Dominator
        d = Dominator(drc)
        splist = [
            FakeSource('1.0-1',PackagePublishingStatus.PUBLISHED,'foo'),
            FakeSource('1.0-2',PackagePublishingStatus.PUBLISHED,'foo'),
            FakeSource('1.0-1',PackagePublishingStatus.PUBLISHED,'bar')
            ]
        bplist = [
            FakeBinary('1.0-1',PackagePublishingStatus.PUBLISHED,'foo'),
            FakeBinary('1.0-2',PackagePublishingStatus.PUBLISHED,'foo'),
            FakeBinary('1.0-1',PackagePublishingStatus.PUBLISHED,'bar')
            ]
        d.dominate(splist,bplist)
        self.assertEqual(splist[0].status, PackagePublishingStatus.SUPERCEDED)
        self.assertEqual(splist[1].status, PackagePublishingStatus.PUBLISHED)
        self.assertEqual(splist[2].status, PackagePublishingStatus.PUBLISHED)
        self.assertEqual(bplist[0].status, PackagePublishingStatus.SUPERCEDED)
        self.assertEqual(bplist[1].status, PackagePublishingStatus.PUBLISHED)
        self.assertEqual(bplist[2].status, PackagePublishingStatus.PUBLISHED)


def test_suite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestDominator))
    return suite

def main(argv):
    suite = test_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    if not runner.run(suite).wasSuccessful():
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

