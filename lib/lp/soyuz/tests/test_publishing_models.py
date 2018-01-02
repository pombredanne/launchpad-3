# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test model and set utilities used for publishing."""

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.app.errors import NotFoundError
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.sourcepackage import SourcePackageFileType
from lp.services.database.constants import UTC_NOW
from lp.services.librarian.browser import ProxiedLibraryFileAlias
from lp.services.webapp.publisher import canonical_url
from lp.soyuz.enums import (
    BinaryPackageFileType,
    BinaryPackageFormat,
    )
from lp.soyuz.interfaces.publishing import (
    IPublishingSet,
    PackagePublishingStatus,
    )
from lp.soyuz.tests.test_binarypackagebuild import BaseTestCaseWithThreeBuilds
from lp.testing import TestCaseWithFactory
from lp.testing.layers import (
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    )


class TestPublishingSet(BaseTestCaseWithThreeBuilds):
    """Tests the IPublishingSet utility implementation."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Use `SoyuzTestPublisher` to publish some sources in archives."""
        super(TestPublishingSet, self).setUp()

        # Ensure all the builds have been built.
        for build in self.builds:
            build.updateStatus(BuildStatus.FULLYBUILT)
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
        bpr = self.factory.makeBinaryPackageRelease(
            build=self.builds[0], architecturespecific=True)
        self.factory.makeBinaryPackagePublishingHistory(
            binarypackagerelease=bpr, archive=self.sources[0].archive,
            distroarchseries=self.builds[0].distro_arch_series,
            pocket=self.sources[0].pocket,
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
        bpr = self.factory.makeBinaryPackageRelease(
            build=self.builds[0], architecturespecific=True)
        bpph = self.factory.makeBinaryPackagePublishingHistory(
            binarypackagerelease=bpr, archive=self.sources[0].archive,
            distroarchseries=self.builds[0].distro_arch_series,
            pocket=self.sources[0].pocket,
            status=PackagePublishingStatus.PUBLISHED)
        bpph.supersede()

        results = self.publishing_set.getUnpublishedBuildsForSources(
            self.sources)
        unpublished_builds = self._getBuildsForResults(results)

        # The original gedit build should not be included in the results as,
        # even though it is no longer published.
        self.assertContentEqual(self.builds[1:3], unpublished_builds)

    def test_getChangesFileLFA(self):
        # The getChangesFileLFA() method finds the right LFAs.
        for spph, name in zip(self.sources, ('foo', 'bar', 'baz')):
            pu = self.factory.makePackageUpload(
                archive=spph.sourcepackagerelease.upload_archive,
                distroseries=spph.sourcepackagerelease.upload_distroseries,
                changes_filename='%s_666_source.changes' % name)
            pu.addSource(spph.sourcepackagerelease)
            pu.setDone()

        lfas = (
            self.publishing_set.getChangesFileLFA(hist.sourcepackagerelease)
            for hist in self.sources)
        urls = [lfa.http_url for lfa in lfas]
        self.assertTrue(urls[0].endswith('/foo_666_source.changes'))
        self.assertTrue(urls[1].endswith('/bar_666_source.changes'))
        self.assertTrue(urls[2].endswith('/baz_666_source.changes'))


class TestSourcePackagePublishingHistory(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_ancestry(self):
        """Ancestry can be traversed."""
        ancestor = self.factory.makeSourcePackagePublishingHistory()
        spph = self.factory.makeSourcePackagePublishingHistory(
            ancestor=ancestor)
        self.assertEqual(spph.ancestor.displayname, ancestor.displayname)

    def test_changelogUrl_missing(self):
        spr = self.factory.makeSourcePackageRelease(changelog=None)
        spph = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagerelease=spr)
        self.assertEqual(None, spph.changelogUrl())

    def test_changelogUrl(self):
        spr = self.factory.makeSourcePackageRelease(
            changelog=self.factory.makeChangelog('foo', ['1.0']))
        spph = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagerelease=spr)
        self.assertEqual(
            canonical_url(spph) + '/+files/%s' % spr.changelog.filename,
            spph.changelogUrl())

    def test_getFileByName_changelog(self):
        spr = self.factory.makeSourcePackageRelease(
            changelog=self.factory.makeLibraryFileAlias(filename='changelog'))
        spph = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagerelease=spr)
        self.assertEqual(spr.changelog, spph.getFileByName('changelog'))

    def test_getFileByName_changelog_absent(self):
        spr = self.factory.makeSourcePackageRelease(changelog=None)
        spph = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagerelease=spr)
        self.assertRaises(NotFoundError, spph.getFileByName, 'changelog')

    def test_getFileByName_unhandled_name(self):
        spph = self.factory.makeSourcePackagePublishingHistory()
        self.assertRaises(NotFoundError, spph.getFileByName, 'not-changelog')

    def getURLsForSPPH(self, spph, include_meta=False):
        spr = spph.sourcepackagerelease
        archive = spph.archive
        urls = [ProxiedLibraryFileAlias(f.libraryfile, archive).http_url
            for f in spr.files]

        if include_meta:
            meta = [(
                f.libraryfile.content.filesize,
                f.libraryfile.content.sha256,
            ) for f in spr.files]

            return [dict(url=url, size=size, sha256=sha256)
                for url, (size, sha256) in zip(urls, meta)]
        return urls

    def makeSPPH(self, num_files=1):
        archive = self.factory.makeArchive(private=False)
        spr = self.factory.makeSourcePackageRelease(archive=archive)
        filetypes = [
            SourcePackageFileType.DSC, SourcePackageFileType.ORIG_TARBALL]
        for count in range(num_files):
            self.factory.makeSourcePackageReleaseFile(
                sourcepackagerelease=spr, filetype=filetypes[count % 2])
        return self.factory.makeSourcePackagePublishingHistory(
            sourcepackagerelease=spr, archive=archive)

    def test_sourceFileUrls_no_files(self):
        spph = self.makeSPPH(num_files=0)

        urls = spph.sourceFileUrls()

        self.assertContentEqual([], urls)

    def test_sourceFileUrls_one_file(self):
        spph = self.makeSPPH(num_files=1)

        urls = spph.sourceFileUrls()

        self.assertContentEqual(self.getURLsForSPPH(spph), urls)

    def test_sourceFileUrls_two_files(self):
        spph = self.makeSPPH(num_files=2)

        urls = spph.sourceFileUrls()

        self.assertContentEqual(self.getURLsForSPPH(spph), urls)

    def test_sourceFileUrls_include_meta(self):
        spph = self.makeSPPH(num_files=2)

        urls = spph.sourceFileUrls(include_meta=True)

        self.assertContentEqual(
            self.getURLsForSPPH(spph, include_meta=True), urls)


class TestBinaryPackagePublishingHistory(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def getURLsForBPPH(self, bpph, include_meta=False):
        bpr = bpph.binarypackagerelease
        archive = bpph.archive
        urls = [ProxiedLibraryFileAlias(f.libraryfile, archive).http_url
            for f in bpr.files]

        if include_meta:
            meta = [(
                f.libraryfile.content.filesize,
                f.libraryfile.content.sha1,
                f.libraryfile.content.sha256,
            ) for f in bpr.files]

            return [dict(url=url, size=size, sha1=sha1, sha256=sha256)
                for url, (size, sha1, sha256) in zip(urls, meta)]
        return urls

    def makeBPPH(self, num_binaries=1):
        archive = self.factory.makeArchive(private=False)
        bpr = self.factory.makeBinaryPackageRelease()
        filetypes = [BinaryPackageFileType.DEB, BinaryPackageFileType.DDEB]
        for count in range(num_binaries):
            self.factory.makeBinaryPackageFile(binarypackagerelease=bpr,
                                               filetype=filetypes[count % 2])
        return self.factory.makeBinaryPackagePublishingHistory(
            binarypackagerelease=bpr, archive=archive)

    def test_binaryFileUrls_no_binaries(self):
        bpph = self.makeBPPH(num_binaries=0)

        urls = bpph.binaryFileUrls()

        self.assertContentEqual([], urls)

    def test_binaryFileUrls_one_binary(self):
        bpph = self.makeBPPH(num_binaries=1)

        urls = bpph.binaryFileUrls()

        self.assertContentEqual(self.getURLsForBPPH(bpph), urls)

    def test_binaryFileUrls_two_binaries(self):
        bpph = self.makeBPPH(num_binaries=2)

        urls = bpph.binaryFileUrls()

        self.assertContentEqual(self.getURLsForBPPH(bpph), urls)

    def test_binaryFileUrls_include_meta(self):
        bpph = self.makeBPPH(num_binaries=2)

        urls = bpph.binaryFileUrls(include_meta=True)

        self.assertContentEqual(
            self.getURLsForBPPH(bpph, include_meta=True), urls)

    def test_binaryFileUrls_removed(self):
        # binaryFileUrls returns URLs even if the files have been removed
        # from the published archive.
        bpph = self.makeBPPH(num_binaries=2)
        expected_urls = self.getURLsForBPPH(bpph)
        expected_urls_meta = self.getURLsForBPPH(bpph, include_meta=True)
        self.assertContentEqual(expected_urls, bpph.binaryFileUrls())
        self.assertContentEqual(
            expected_urls_meta, bpph.binaryFileUrls(include_meta=True))
        removeSecurityProxy(bpph).dateremoved = UTC_NOW
        self.assertContentEqual(expected_urls, bpph.binaryFileUrls())
        self.assertContentEqual(
            expected_urls_meta, bpph.binaryFileUrls(include_meta=True))

    def test_is_debug_false_for_deb(self):
        bpph = self.factory.makeBinaryPackagePublishingHistory(
            binpackageformat=BinaryPackageFormat.DEB)
        self.assertFalse(bpph.is_debug)

    def test_is_debug_true_for_ddeb(self):
        bpph = self.factory.makeBinaryPackagePublishingHistory(
            binpackageformat=BinaryPackageFormat.DDEB)
        self.assertTrue(bpph.is_debug)
