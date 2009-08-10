# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test model and set utilities used for publishing."""

import unittest

from zope.component import getUtility

from canonical.database.constants import UTC_NOW
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

        # Ensure all the builds have been built.
        for build in self.builds:
            build.buildstate = BuildStatus.FULLYBUILT
        self.publishing_set = getUtility(IPublishingSet)

    def _getBuildsForResults(self, results):
        # The method returns (SPPH, Build) tuples, we just want the build.
        return [result[1] for result in results]

    def test_getUnpublishedBuildsForSources_none_published(self):
        # If no binaries have been published then all builds are.
        results = self.publishing_set.getUnpublishedBuildsForSources(
            self.sources)
        unpublished_builds = self._getBuildsForResults(results)

        self.assertContentEqual(self.builds, unpublished_builds)

    def test_getUnpublishedBuildsForSources_one_published(self):
        # If we publish a binary for a build, it is no longer returned.
        bpr = self.publisher.uploadBinaryForBuild(self.builds[0], 'gedit')
        bpph = self.publisher.publishBinaryInArchive(
            bpr, self.sources[0].archive,
            status=PackagePublishingStatus.PUBLISHED)

        results = self.publishing_set.getUnpublishedBuildsForSources(
            self.sources)
        unpublished_builds = self._getBuildsForResults(results)

        self.assertContentEqual(self.builds[1:3], unpublished_builds)

    def test_getUnpublishedBuildsForSources_with_cruft(self):
        # SourcePackages that has a superseded binary are still considered
        # 'published'.

        # Publish the binaries for gedit as superseded, explicitly setting
        # the date published.
        bpr = self.publisher.uploadBinaryForBuild(self.builds[0], 'gedit')
        bpphs = self.publisher.publishBinaryInArchive(
            bpr, self.sources[0].archive,
            status=PackagePublishingStatus.SUPERSEDED)
        for bpph in bpphs:
            bpph.secure_record.datepublished = UTC_NOW

        results = self.publishing_set.getUnpublishedBuildsForSources(
            self.sources)
        unpublished_builds = self._getBuildsForResults(results)

        # The original gedit build should not be included in the results as,
        # even though it is no longer published.
        self.assertContentEqual(self.builds[1:3], unpublished_builds)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
