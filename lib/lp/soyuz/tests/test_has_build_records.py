# Copyright 2009 Canonical Ltd.  All rights reserved.
"""Test implementations of the IHasBuildRecords interface."""

import unittest

from canonical.testing import LaunchpadZopelessLayer

from lp.soyuz.interfaces.buildrecords import IHasBuildRecords
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
            status=PackagePublishingStatus.PUBLISHED)
        self.builds += gtg_src_hist.createMissingBuilds()


class TestHasBuildRecordsInterface(TestCaseWithPublishedBuilds):
    """Tests the implementation of IHasBuildRecords by the
       Distribution content class by default.

       Inherit and set self.context to another content class to test it.
    """
    def setUp(self):
        """Use `SoyuzTestPublisher` to publish some sources in archives."""
        super(TestHasBuildRecordsInterface, self).setUp()

        self.context = self.publisher.distroseries.distribution

    def testProvidesHasBuildRecords(self):
        # Ensure that the context does in fact provide IHasBuildRecords
        self.assertProvides(self.context, IHasBuildRecords)

    def testGetBuildRecordsNoArgs(self):
        # getBuildRecords() called without any arguments returns all builds.
        builds = self.context.getBuildRecords()
        num_results = builds.count()
        self.assertEquals(3, num_results, "Expected 3 builds but "
                                          "got %s" % num_results)

    def testGetBuildRecordsFilterByArchTag(self):
        # Build records can be filtered by architecture tag.

        # Target one of the builds to hppa
        self.builds[0].distroarchseries = self.publisher.distroseries['hppa']
        builds = self.context.getBuildRecords(arch_tag="i386")
        num_results = builds.count()
        self.assertEquals(2, num_results, "Expected 2 builds but "
                                          "got %s" % num_results)


class TestDistroSeriesHasBuildRecords(TestHasBuildRecordsInterface):
    """Test the DistroSeries implementation of IHasBuildRecords."""
    def setUp(self):
        super(TestDistroSeriesHasBuildRecords, self).setUp()

        self.context = self.publisher.distroseries


class TestDistroArchSeriesHasBuildRecords(TestHasBuildRecordsInterface):
    """Test the DistroArchSeries implementation of IHasBuildRecords."""
    def setUp(self):
        super(TestDistroArchSeriesHasBuildRecords, self).setUp()

        self.context = self.publisher.distroseries['i386']


class TestArchiveHasBuildRecords(TestHasBuildRecordsInterface):
    """Test the DistroArchSeries implementation of IHasBuildRecords."""
    def setUp(self):
        super(TestArchiveHasBuildRecords, self).setUp()

        self.context = self.publisher.distroseries.main_archive


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
