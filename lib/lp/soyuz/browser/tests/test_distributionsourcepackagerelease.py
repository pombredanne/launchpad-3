# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for TestSourcePackageReleaseFiles."""

__metaclass__ = type
__all__ = [
    'TestDistributionSourcePackageReleaseFiles',
    ]

from zope.security.proxy import removeSecurityProxy

from lp.services.webapp import canonical_url
from lp.testing import TestCaseWithFactory
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.publication import test_traverse
from lp.testing.views import create_initialized_view


class TestDistributionSourcePackageReleaseNavigation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUpLatestBuildTests(self):
        distribution = self.factory.makeDistribution()
        dses = [
            self.factory.makeDistroSeries(distribution=distribution)
            for i in range(2)]
        spr = self.factory.makeSourcePackageRelease(distroseries=dses[0])
        proc = self.factory.makeProcessor()
        builds = []
        for i in range(2):
            self.factory.makeSourcePackagePublishingHistory(
                distroseries=dses[0], sourcepackagerelease=spr)
            das = self.factory.makeDistroArchSeries(
                distroseries=dses[i], architecturetag="arch", processor=proc)
            builds.append(self.factory.makeBinaryPackageBuild(
                source_package_release=spr, distroarchseries=das))
        builds.append(
            self.factory.makeBinaryPackageBuild(source_package_release=spr))
        return canonical_url(distribution.getSourcePackageRelease(spr)), builds

    def test_latestbuild_known_arch(self):
        # +latestbuild redirects to the most recent build for the requested
        # architecture.
        dspr_url, builds = self.setUpLatestBuildTests()
        _, view, _ = test_traverse("%s/+latestbuild/arch" % dspr_url)
        self.assertEqual(
            canonical_url(builds[1]), removeSecurityProxy(view).target)
        self.assertEqual(303, removeSecurityProxy(view).status)

    def test_latestbuild_unknown_arch(self):
        # If there is no build for the requested architecture, +latestbuild
        # redirects to the context DSPR.
        dspr_url, _ = self.setUpLatestBuildTests()
        obj, view, _ = test_traverse("%s/+latestbuild/unknown" % dspr_url)
        self.assertEqual(dspr_url, canonical_url(obj))
        self.assertEqual(303, removeSecurityProxy(view).status)


class TestDistributionSourcePackageReleaseFiles(TestCaseWithFactory):
    """Source package release files are rendered correctly."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestDistributionSourcePackageReleaseFiles, self).setUp()
        # SourcePackageRelease itself is contextless, so wrap it in DSPR
        # to give it a URL.
        spr = self.factory.makeSourcePackageRelease()
        distroseries = self.factory.makeDistroSeries()
        self.factory.makeSourcePackagePublishingHistory(
            archive=distroseries.main_archive, distroseries=distroseries,
            sourcepackagerelease=spr)
        self.source_package_release = (
            distroseries.distribution.getSourcePackageRelease(spr))

    def test_spr_files_none(self):
        # The snippet renders appropriately when there are no files.
        view = create_initialized_view(self.source_package_release, "+files")
        html = view.__call__()
        self.failUnless('No files available for download.' in html)

    def test_spr_files_one(self):
        # The snippet links to the file when present.
        library_file = self.factory.makeLibraryFileAlias(
            filename='test_file.dsc', content='0123456789')
        self.source_package_release.addFile(library_file)
        view = create_initialized_view(self.source_package_release, "+files")
        html = view.__call__()
        self.failUnless('test_file.dsc' in html)

    def test_spr_files_deleted(self):
        # The snippet handles deleted files too.
        library_file = self.factory.makeLibraryFileAlias(
            filename='test_file.dsc', content='0123456789')
        self.source_package_release.addFile(library_file)
        removeSecurityProxy(library_file).content = None
        view = create_initialized_view(self.source_package_release, "+files")
        html = view.__call__()
        self.failUnless('test_file.dsc (deleted)' in html)
