#!/usr/bin/env python

# Copyright 2004 Canonical Ltd.  All rights reserved.
#

import unittest
import sys
import os
import shutil

from canonical.archivepublisher.tests.util import dist, drs
     
class TestConfig(unittest.TestCase):

    def testImport(self):
        """canonical.archivepublisher.Config should be importable"""
        from canonical.archivepublisher import Config

    def testInstantiate(self):
        """canonical.archivepublisher.Config should instantiate"""
        from canonical.archivepublisher import Config
        d = Config(dist, drs)

    def testDistroName(self):
        """canonical.archivepublisher.Config should be able to return the distroName"""
        from canonical.archivepublisher import Config
        d = Config(dist, drs)
        self.assertEqual( d.distroName, "ubuntu" )

    def testDistroReleaseNames(self):
        """canonical.archivepublisher.Config should return two distrorelease names"""
        from canonical.archivepublisher import Config
        d = Config(dist, drs)
        drns = d.distroReleaseNames()
        self.assertEquals( len(drns), 2 )
        if drns[0].startswith("h"):
            self.assertEquals( drns[0], "hoary" )
            self.assertEquals( drns[1], "warty" )
        else:
            self.assertEquals( drns[0], "warty" )
            self.assertEquals( drns[1], "hoary" )

    def testArchTagsForRelease(self):
        """canonical.archivepublisher.Config should have the arch tags for the drs"""
        from canonical.archivepublisher import Config
        d = Config(dist, drs)
        archs = d.archTagsForRelease( "hoary" )
        self.assertEquals( len(archs), 2 )

    def testDistroConfig(self):
        """canonical.archivepublisher.Config should have parsed a distro config"""
        from canonical.archivepublisher import Config
        d = Config(dist, drs)
        # NOTE: Add checks here when you add stuff in util.py
        self.assertEquals( d.stayofexecution, 5 )


        
def test_suite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestConfig))
    return suite

def main(argv):
    suite = test_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    if not runner.run(suite).wasSuccessful():
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

