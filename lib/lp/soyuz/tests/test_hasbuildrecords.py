# Copyright 2009 Canonical Ltd.  All rights reserved.
"""Test implementations of the IHasBuildRecords interface."""

import unittest

from zope.component import getUtility

from canonical.testing import LaunchpadZopelessLayer

from lp.registry.model.sourcepackage import SourcePackage
from lp.soyuz.interfaces.builder import IBuilderSet
from lp.soyuz.interfaces.buildrecords import IHasBuildRecords
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.model.processor import ProcessorFamilySet
from lp.soyuz.tests.test_build import BaseTestCaseWithThreeBuilds
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher

class TestHasBuildRecordsInterface(BaseTestCaseWithThreeBuilds):
    """Tests the implementation of IHasBuildRecords by the
       Distribution content class by default.

       Inherit and set self.context to another content class to test
       other implementations.
    """

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Use `SoyuzTestPublisher` to publish some sources in archives."""
        super(TestHasBuildRecordsInterface, self).setUp()

        self.context = self.publisher.distroseries.distribution

    def testProvidesHasBuildRecords(self):
        # Ensure that the context does in fact provide IHasBuildRecords
        self.assertCorrectlyProvides(self.context, IHasBuildRecords)

    def test_getBuildRecords_no_archs(self):
        # getBuildRecords() called without any arguments returns all builds.
        builds = self.context.getBuildRecords()
        self.assertContentEqual(builds, self.builds)

    def test_getBuildRecords_by_arch_tag(self):
        # Build records can be filtered by architecture tag.

        # Target one of the builds to hppa so that we have three builds
        # in total, two of which are i386 and one hppa.
        i386_builds = self.builds[:]
        hppa_build = i386_builds.pop()
        hppa_build.distroarchseries = self.publisher.distroseries['hppa']

        builds = self.context.getBuildRecords(arch_tag="i386")
        self.assertContentEqual(i386_builds, builds)


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
    """Test the Archive implementation of IHasBuildRecords."""
    def setUp(self):
        super(TestArchiveHasBuildRecords, self).setUp()

        self.context = self.publisher.distroseries.main_archive


class TestBuilderHasBuildRecords(TestHasBuildRecordsInterface):
    """Test the Builder implementation of IHasBuildRecords."""
    def setUp(self):
        super(TestBuilderHasBuildRecords, self).setUp()

        # Create a 386 builder
        owner = self.factory.makePerson()
        processor_family = ProcessorFamilySet().getByProcessorName('386')
        processor = processor_family.processors[0]
        builder_set = getUtility(IBuilderSet)
        self.context = builder_set.new(
            processor, 'http://example.com', 'Newbob', 'New Bob the Builder',
            'A new and improved bob.', owner)

        # Ensure that our builds were all built by the test builder.
        for build in self.builds:
            build.builder = self.context


class TestSourcePackageHasBuildRecords(TestHasBuildRecordsInterface):
    """Test the SourcePackage implementation of IHasBuildRecords."""
    def setUp(self):
        super(TestSourcePackageHasBuildRecords, self).setUp()

        gedit_name = self.builds[0].sourcepackagerelease.sourcepackagename
        self.context = SourcePackage(
            gedit_name,
            self.builds[0].distroarchseries.distroseries)

        # Convert the other two builds to be builds of
        # gedit as well so that the one source package (gedit) will have
        # three builds.
        self.builds[1].sourcepackagerelease.sourcepackagename = gedit_name
        self.builds[2].sourcepackagerelease.sourcepackagename = gedit_name


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
