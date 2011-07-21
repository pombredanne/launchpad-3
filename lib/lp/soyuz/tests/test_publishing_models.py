# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test model and set utilities used for publishing."""

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.database.constants import UTC_NOW
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.buildmaster.enums import BuildStatus
from lp.soyuz.interfaces.publishing import (
    IPublishingSet,
    PackagePublishingStatus,
    )
from lp.soyuz.tests.test_binarypackagebuild import BaseTestCaseWithThreeBuilds


class TestPublishingSet(BaseTestCaseWithThreeBuilds):
    """Tests the IPublishingSet utility implementation."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Use `SoyuzTestPublisher` to publish some sources in archives."""
        super(TestPublishingSet, self).setUp()

        # Ensure all the builds have been built.
        for build in self.builds:
            removeSecurityProxy(build).status = BuildStatus.FULLYBUILT
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
            bpph.datepublished = UTC_NOW

        results = self.publishing_set.getUnpublishedBuildsForSources(
            self.sources)
        unpublished_builds = self._getBuildsForResults(results)

        # The original gedit build should not be included in the results as,
        # even though it is no longer published.
        self.assertContentEqual(self.builds[1:3], unpublished_builds)

    def test_getChangesFileLFA(self):
        # The getChangesFileLFA() method finds the right LFAs.
        lfas = (
            self.publishing_set.getChangesFileLFA(hist.sourcepackagerelease)
            for hist in self.sources)
        urls = [lfa.http_url for lfa in lfas]
        self.assert_(urls[0].endswith('/94/gedit_666_source.changes'))
        self.assert_(urls[1].endswith('/96/firefox_666_source.changes'))
        self.assert_(urls[2].endswith(
            '/98/getting-things-gnome_666_source.changes'))
