# Copyright 2009 Canonical Ltd.  All rights reserved.
"""Test implementations of the IHasBuildRecords interface."""

import unittest

from canonical.testing import LaunchpadZopelessLayer

from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory

class TestCaseWithPublishedBuilds(TestCaseWithFactory):
    """Adds a SoyuzTestPublisher instance during setup."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestCaseWithPublishedBuilds, self).setUp()
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        # Create three builds for the publisher's default
        # distroseries.
        self.builds = []
        gedit_src_hist = self.publisher.getPubSource(
            sourcename="gedit", status=PackagePublishingStatus.PUBLISHED)
        self.builds += gedit_src_hist.createMissingBuilds()

        firefox_src_hist = self.publisher.getPubSource(
            sourcename="firefox", status=PackagePublishingStatus.PUBLISHED)
        self.builds += firefox_src_hist.createMissingBuilds()

        gtg_src_hist = self.publisher.getPubSource(
            sourcename="getting-things-gnome",
            architecturehintlist="i386",
            status=PackagePublishingStatus.PUBLISHED)
        self.builds += gtg_src_hist.createMissingBuilds()


class TestDistroSeriesHasBuildRecords(TestCaseWithPublishedBuilds):
    """Test the DistroSeries implementation of
       IHasBuildRecords.getBuildRecords().
    """
    def setUp(self):
        """Use `SoyuzTestPublisher` to publish some sources in archives."""
        super(TestDistroSeriesHasBuildRecords, self).setUp()

        self.distroseries = self.publisher.distroseries

    def testGetBuildRecordsNoArgs(self):
        # getBuildRecords() called without any arguments returns all builds.
        builds = self.distroseries.getBuildRecords()
        num_results = builds.count()
        self.assertEquals(3, num_results, "Expected 3 builds but "
                                          "got %s" % num_results)

    def testGetBuildRecordsFilterByArchTag(self):
        # Build records can be filtered by architecture tag.
        builds = self.distroseries.getBuildRecords(arch_tag="hppa")
        num_results = builds.count()
        self.assertEquals(0, num_results, "Expected 0 builds but "
                                          "got %s" % num_results)

        # Target one of the builds to hppa
        self.builds[0].distroarchseries = self.distroseries['hppa']
        builds = self.distroseries.getBuildRecords(arch_tag="hppa")
        num_results = builds.count()
        self.assertEquals(1, num_results, "Expected 1 build but "
                                          "got %s" % num_results)


class TestDistributionHasBuildRecords(TestCaseWithPublishedBuilds):
    def setUp(self):
        super(TestDistributionHasBuildRecords, self).setUp()

        self.distribution = self.publisher.distroseries.distribution

    def testGetBuildRecordsNoArgs(self):
        # getBuildRecords() called without any arguments returns all builds.
        builds = self.distribution.getBuildRecords()
        num_results = builds.count()
        self.assertEquals(3, num_results, "Expected 3 builds but "
                                          "got %s." % num_results)

    def testGetBuildRecordsFilterByArchTag(self):
        # Build records can be filtered by architecture tag.
        builds = self.distribution.getBuildRecords(arch_tag="hppa")
        num_results = builds.count()
        self.assertEquals(0, num_results, "Expected 0 builds but "
                                          "got %s" % num_results)

        # Target one of the builds to hppa
        self.builds[0].distroarchseries = self.publisher.distroseries['hppa']
        builds = self.distribution.getBuildRecords(arch_tag="hppa")
        num_results = builds.count()
        self.assertEquals(1, num_results, "Expected 1 build but "
                                          "got %s" % num_results)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
