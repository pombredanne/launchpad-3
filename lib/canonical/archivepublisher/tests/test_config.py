#!/usr/bin/env python

# Copyright 2004 Canonical Ltd.  All rights reserved.
#

import unittest
import sys
import os
import shutil

from zope.component import getUtility

from canonical.functional import ZopelessLayer
from canonical.launchpad.ftests.harness import (
    LaunchpadZopelessTestCase, LaunchpadZopelessTestSetup)
from canonical.launchpad.interfaces import IDistributionSet


class TestConfig(LaunchpadZopelessTestCase):
    layer = ZopelessLayer
    dbuser = 'lucille'

    def setUp(self):
        LaunchpadZopelessTestCase.setUp(self)
        self.ubuntutest = getUtility(IDistributionSet)['ubuntutest']

    def testImport(self):
        """canonical.archivepublisher.Config should be importable"""
        from canonical.archivepublisher import Config

    def testInstantiate(self):
        """Config should instantiate"""
        from canonical.archivepublisher import Config
        d = Config(self.ubuntutest)

    def testDistroName(self):
        """Config should be able to return the distroName"""
        from canonical.archivepublisher import Config
        d = Config(self.ubuntutest)
        self.assertEqual(d.distroName, "ubuntutest")

    def testDistroReleaseNames(self):
        """Config should return two distrorelease names"""
        from canonical.archivepublisher import Config
        d = Config(self.ubuntutest)
        drns = d.distroReleaseNames()
        self.assertEquals( len(drns), 2 )
        if drns[0].startswith("h"):
            self.assertEquals(drns[0], "breezy-autotest")
            self.assertEquals(drns[1], "hoary")
        else:
            self.assertEquals(drns[0], "breezy-autotest")
            self.assertEquals(drns[1], "hoary")

    def testArchTagsForRelease(self):
        """Config should have the arch tags for the drs"""
        from canonical.archivepublisher import Config
        d = Config(self.ubuntutest)
        archs = d.archTagsForRelease("hoary")
        self.assertEquals( len(archs), 2)

    def testDistroConfig(self):
        """Config should have parsed a distro config"""
        from canonical.archivepublisher import Config
        d = Config(self.ubuntutest)
        # NOTE: Add checks here when you add stuff in util.py
        self.assertEquals(d.stayofexecution, 5)


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

