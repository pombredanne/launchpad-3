# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=F0401

"""Unit tests for TestSourcePackageReleaseFiles."""

__metaclass__ = type
__all__ = [
    'TestSourcePackageReleaseFiles',
    'test_suite',
    ]

from zope.security.proxy import removeSecurityProxy

from canonical.testing import LaunchpadFunctionalLayer
from lp.testing import TestCaseWithFactory
from lp.testing.views import create_initialized_view


class TestSourcePackageReleaseFiles(TestCaseWithFactory):
    """Source package release files are rendered correctly."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestSourcePackageReleaseFiles, self).setUp()
        self.source_package_release = self.factory.makeSourcePackageRelease()

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
