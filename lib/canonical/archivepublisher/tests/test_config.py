# Copyright 2004 Canonical Ltd.  All rights reserved.
#

"""Tests for Config.py"""

__metaclass__ = type

import unittest
import sys

from canonical.archivepublisher.tests.util import (
    fake_ubuntu, fake_ubuntu_releases)
     
class TestConfig(unittest.TestCase):

    def testImport(self):
        """canonical.archivepublisher.Config should be importable"""
        from canonical.archivepublisher import Config

    def testInstantiate(self):
        """canonical.archivepublisher.Config should instantiate"""
        from canonical.archivepublisher import Config
        d = Config(fake_ubuntu, fake_ubuntu_releases)

    def testDistroName(self):
        """canonical.archivepublisher.Config should be able to return the distroName"""
        from canonical.archivepublisher import Config
        d = Config(fake_ubuntu, fake_ubuntu_releases)
        self.assertEqual( d.distroName, "ubuntu" )

    def testDistroReleaseNames(self):
        """canonical.archivepublisher.Config should return two distrorelease names"""
        from canonical.archivepublisher import Config
        d = Config(fake_ubuntu, fake_ubuntu_releases)
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
        d = Config(fake_ubuntu, fake_ubuntu_releases)
        archs = d.archTagsForRelease( "hoary" )
        self.assertEquals( len(archs), 2 )

    def testDistroConfig(self):
        """canonical.archivepublisher.Config should have parsed a distro config"""
        from canonical.archivepublisher import Config
        d = Config(fake_ubuntu, fake_ubuntu_releases)
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

