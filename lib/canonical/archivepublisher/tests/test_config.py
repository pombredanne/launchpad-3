# Copyright 2004 Canonical Ltd.  All rights reserved.
#

"""Tests for Config.py"""

__metaclass__ = type

from unittest import TestLoader

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.ftests.harness import (
    LaunchpadZopelessTestCase)
from canonical.launchpad.interfaces import IDistributionSet


class TestConfig(LaunchpadZopelessTestCase):

    dbuser = config.archivepublisher.dbuser

    def setUp(self):
        LaunchpadZopelessTestCase.setUp(self)
        self.ubuntutest = getUtility(IDistributionSet)['ubuntutest']

    def testInstantiate(self):
        """Config should instantiate"""
        from canonical.archivepublisher.config import Config
        d = Config(self.ubuntutest)

    def testDistroName(self):
        """Config should be able to return the distroName"""
        from canonical.archivepublisher.config import Config
        d = Config(self.ubuntutest)
        self.assertEqual(d.distroName, "ubuntutest")

    def testDistroSeriesNames(self):
        """Config should return two distroseries names"""
        from canonical.archivepublisher.config import Config
        d = Config(self.ubuntutest)
        dsns = d.distroSeriesNames()
        self.assertEquals(len(dsns), 2)
        self.assertEquals(dsns[0], "breezy-autotest")
        self.assertEquals(dsns[1], "hoary-test")

    def testArchTagsForSeries(self):
        """Config should have the arch tags for the drs"""
        from canonical.archivepublisher.config import Config
        d = Config(self.ubuntutest)
        archs = d.archTagsForSeries("hoary-test")
        self.assertEquals( len(archs), 2)

    def testDistroConfig(self):
        """Config should have parsed a distro config"""
        from canonical.archivepublisher.config import Config
        d = Config(self.ubuntutest)
        # NOTE: Add checks here when you add stuff in util.py
        self.assertEquals(d.stayofexecution, 5)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
