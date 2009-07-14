# Copyright 2009 Canonical Ltd.  All rights reserved.
"""Test model and set utilities used for publishing."""

import unittest

from zope.component import getUtility

from canonical.testing import LaunchpadZopelessLayer

from lp.soyuz.interfaces.build import BuildStatus
from lp.soyuz.interfaces.publishing import (IPublishingSet,
    PackagePublishingStatus)
from lp.soyuz.tests.test_build import BaseTestCaseWithThreeBuilds


class TestPublishingSet(BaseTestCaseWithThreeBuilds):
    """Tests the IPublishingSet utility implementation."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Use `SoyuzTestPublisher` to publish some sources in archives."""
        super(TestPublishingSet, self).setUp()

        # Ensure all the builds have been built
        for build in self.builds:
            build.buildstate = BuildStatus.FULLYBUILT
        self.publishing_set = getUtility(IPublishingSet)

    def get_builds_for_results(self, results):
        # The method returns (SPPH, Build) tuples, we just want the build.
        return [result[1] for result in results]

    def create_gedit2_source_with_gedit_binary(self, version="999"):
        # Create a new gedit build a gedit binary already published with
        # a later version.
        gedit2_src_hist = self.publisher.getPubSource(
            sourcename="gedit2", status=PackagePublishingStatus.PUBLISHED,
            version=version)
        gedit2_builds = gedit2_src_hist.createMissingBuilds()
        bpr = self.publisher.uploadBinaryForBuild(gedit2_builds[0], 'gedit')

    def test_getUnpublishedBuildsForSources_non_published(self):
        # If no binaries have been published then all builds are.
        results = self.publishing_set.getUnpublishedBuildsForSources(
            self.sources)
        unpublished_builds = self.get_builds_for_results(results)

        self.assertContentEqual(unpublished_builds, self.builds)

    def test_getUnpublishedBuildsForSources_one_published(self):
        # If we publish a binary for a build, it is no longer returned.
        bpr = self.publisher.uploadBinaryForBuild(self.builds[0], 'gedit')
        bpph = self.publisher.publishBinaryInArchive(
            bpr, self.sources[0].archive,
            status=PackagePublishingStatus.PUBLISHED)

        results = self.publishing_set.getUnpublishedBuildsForSources(
            self.sources)
        unpublished_builds = self.get_builds_for_results(results)

        self.assertContentEqual(unpublished_builds, self.builds[1:3])

    def test_getUnpublishedBuildsForSources_with_cruft(self):
        # SourcePackages that generate binaries for which later versions
        # are already published are ignored by default and not included
        # as unpublished builds.

        self.create_gedit2_source_with_gedit_binary()

        results = self.publishing_set.getUnpublishedBuildsForSources(
            self.sources)
        unpublished_builds = self.get_builds_for_results(results)

        # The original gedit build should not be included in the results as,
        # even though it does not have an associated binary published, there
        # is already a gedit-999 published.
        self.assertContentEqual(unpublished_builds, self.builds[1:3])

    def test_getUnpublishedBuildsForSources_with_non_cruft(self):
        # Published versions <= the current version do not count as
        # cruft.
        self.create_gedit2_source_with_gedit_binary(version="555")

        results = self.publishing_set.getUnpublishedBuildsForSources(
            self.sources)
        unpublished_builds = self.get_builds_for_results(results)

        self.assertContentEqual(unpublished_builds, self.builds)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
