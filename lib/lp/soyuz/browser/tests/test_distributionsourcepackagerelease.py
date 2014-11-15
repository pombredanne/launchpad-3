# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for TestSourcePackageReleaseFiles."""

__metaclass__ = type
__all__ = [
    'TestDistributionSourcePackageReleaseFiles',
    ]

from zope.security.proxy import removeSecurityProxy

from lp.testing import TestCaseWithFactory
from lp.testing.layers import LaunchpadFunctionalLayer
from lp.testing.views import create_initialized_view


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
