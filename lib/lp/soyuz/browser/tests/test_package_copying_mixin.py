# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `PackageCopyingMixin`."""

__metaclass__ = type

from zope.component import getUtility

from canonical.testing.layers import ZopelessDatabaseLayer
from lp.soyuz.browser.archive import (
    annotate_pubs_with_versions,
    copy_asynchronously,
    copy_synchronously,
    PackageCopyingMixin,
    partition_pubs_by_archive,
    render_cannotcopy_as_html,
    )
from lp.soyuz.interfaces.archive import CannotCopy
from lp.soyuz.interfaces.distributionjob import IPackageCopyJobSource
from lp.soyuz.enums import SourcePackageFormat
from lp.soyuz.interfaces.sourcepackageformat import (
    ISourcePackageFormatSelectionSet,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.fakemethod import FakeMethod
from lp.testing.views import create_initialized_view


def find_spph_copy(archive, spph):
    """Find copy of `spph`'s package as copied into `archive`"""
    spr = spph.sourcepackagerelease
    return archive.getPublishedSources(
        name=spr.sourcepackagename.name, version=spr.version).one()


class TestPackageCopyingMixin(TestCaseWithFactory):
    """Test lightweight functions and methods."""

    layer = ZopelessDatabaseLayer

    def makeDestinationSeries(self):
        """Create a `DistroSeries` to copy packages into."""
        series = self.factory.makeDistroSeries(
            parent_series=self.factory.makeDistroSeries())
        getUtility(ISourcePackageFormatSelectionSet).add(
            series, SourcePackageFormat.FORMAT_1_0)
        return series

    def makeView(self, distroseries=None):
        if distroseries is None:
            distroseries = self.makeDestinationSeries()
        return create_initialized_view(distroseries, "+localpackagediffs")

    def test_canCopySynchronously_allows_small_synchronous_copies(self):
        packages = [self.factory.getUniqueString() for counter in range(3)]
        self.assertTrue(PackageCopyingMixin().canCopySynchronously(packages))

    def test_canCopySynchronously_disallows_large_synchronous_copies(self):
        packages = [self.factory.getUniqueString() for counter in range(300)]
        self.assertFalse(PackageCopyingMixin().canCopySynchronously(packages))

    def test_partition_pubs_by_archive_maps_archives_to_pubs(self):
        spph = self.factory.makeSourcePackagePublishingHistory()
        self.assertEqual(
            {spph.archive: [spph]}, partition_pubs_by_archive([spph]))

    def test_partition_pubs_by_archive_splits_by_archive(self):
        spphs = [
            self.factory.makeSourcePackagePublishingHistory()
            for counter in xrange(2)]
        mapping = partition_pubs_by_archive(spphs)
        self.assertEqual(
            dict((spph.archive, [spph]) for spph in spphs), mapping)

    def test_partition_pubs_by_archive_clusters_by_archive(self):
        archive = self.factory.makeArchive()
        spphs = [
            self.factory.makeSourcePackagePublishingHistory(archive=archive)
            for counter in xrange(2)]
        mapping = partition_pubs_by_archive(spphs)
        self.assertEqual([archive], mapping.keys())
        self.assertContentEqual(spphs, mapping[archive])

    def test_annotate_pubs_with_versions_lists_packages_and_versions(self):
        spph = self.factory.makeSourcePackagePublishingHistory()
        spr = spph.sourcepackagerelease
        self.assertEqual(
            [(spr.sourcepackagename.name, spr.version)],
            annotate_pubs_with_versions([spph]))

    def test_render_cannotcopy_as_html_lists_errors(self):
        message = self.factory.getUniqueString()
        html_text = render_cannotcopy_as_html(CannotCopy(message)).escapedtext
        self.assertIn(message, html_text)

    def test_render_cannotcopy_as_html_escapes_error(self):
        message = "x<>y"
        html_text = render_cannotcopy_as_html(CannotCopy(message)).escapedtext
        self.assertNotIn(message, html_text)
        self.assertIn("x&lt;&gt;y", html_text)

    def test_copy_synchronously_copies_packages(self):
        spph = self.factory.makeSourcePackagePublishingHistory()
        dest_series = self.makeDestinationSeries()
        archive = dest_series.distribution.main_archive
        pocket = self.factory.getAnyPocket()
        copy_synchronously(
            [spph], archive, dest_series, pocket, include_binaries=False,
            check_permissions=False)
        self.assertNotEqual(None, find_spph_copy(archive, spph))

    def test_copy_asynchronously_does_not_copy_packages(self):
        spph = self.factory.makeSourcePackagePublishingHistory()
        dest_series = self.makeDestinationSeries()
        archive = dest_series.distribution.main_archive
        pocket = self.factory.getAnyPocket()
        copy_asynchronously(
            [spph], archive, dest_series, pocket, include_binaries=False,
            check_permissions=False)
        self.assertEqual(None, find_spph_copy(archive, spph))

    def test_copy_synchronously_lists_packages(self):
        spph = self.factory.makeSourcePackagePublishingHistory()
        dest_series = self.makeDestinationSeries()
        pocket = self.factory.getAnyPocket()
        notice = copy_synchronously(
            [spph], dest_series.distribution.main_archive, dest_series,
            pocket, include_binaries=False,
            check_permissions=False).escapedtext
        self.assertIn(
            spph.sourcepackagerelease.sourcepackagename.name, notice)

    def test_copy_synchronously_escapes_destination_archive(self):
        spph = self.factory.makeSourcePackagePublishingHistory()
        dest_series = self.makeDestinationSeries()
        archive = self.factory.makeArchive(
            displayname="a&b", distribution=dest_series.distribution)
        pocket = self.factory.getAnyPocket()
        notice = copy_synchronously(
            [spph], archive, dest_series, pocket, include_binaries=False,
            check_permissions=False).escapedtext
        self.assertNotIn("a&b", notice)
        self.assertIn("a&amp;b", notice)

    def test_copy_asynchronously_creates_copy_jobs(self):
        spph = self.factory.makeSourcePackagePublishingHistory()
        dest_series = self.makeDestinationSeries()
        pocket = self.factory.getAnyPocket()
        archive = dest_series.distribution.main_archive
        copy_asynchronously(
            [spph], archive, dest_series, pocket, include_binaries=False,
            check_permissions=False)
        jobs = list(getUtility(IPackageCopyJobSource).getActiveJobs(archive))
        self.assertEqual(1, len(jobs))
        spr = spph.sourcepackagerelease
        self.assertEqual(
            [[spr.sourcepackagename.name, spr.version]],
            jobs[0].metadata['source_packages'])

    def test_copy_asynchronously_groups_jobs_by_dest_archive(self):
        dest_series = self.makeDestinationSeries()
        archive = self.factory.makeArchive(
            distribution=dest_series.distribution)
        spphs = [
            self.factory.makeSourcePackagePublishingHistory(archive=archive)
            for counter in xrange(2)]
        pocket = self.factory.getAnyPocket()
        copy_asynchronously(
            spphs, archive, dest_series, pocket, include_binaries=False,
            check_permissions=False)
        jobs = list(getUtility(IPackageCopyJobSource).getActiveJobs(archive))
        self.assertEqual(1, len(jobs))
        expected = [
            [
                spph.sourcepackagerelease.sourcepackagename.name,
                spph.sourcepackagerelease.version,
            ]
            for spph in spphs]
        self.assertContentEqual(expected, jobs[0].metadata['source_packages'])

    def test_copy_asynchronously_splits_jobs_by_dest_archive(self):
        spphs = [
            self.factory.makeSourcePackagePublishingHistory()
            for counter in xrange(2)]
        dest_series = self.makeDestinationSeries()
        pocket = self.factory.getAnyPocket()
        archive = dest_series.distribution.main_archive
        copy_asynchronously(
            spphs, archive, dest_series, pocket, include_binaries=False,
            check_permissions=False)
        jobs = list(getUtility(IPackageCopyJobSource).getActiveJobs(archive))
        self.assertEqual(2, len(jobs))

    def test_copy_asynchronously_gives_feedback(self):
        spphs = [
            self.factory.makeSourcePackagePublishingHistory()
            for counter in xrange(2)]
        dest_series = self.makeDestinationSeries()
        pocket = self.factory.getAnyPocket()
        notice = copy_asynchronously(
            spphs, dest_series.distribution.main_archive, dest_series,
            pocket, include_binaries=False).escapedtext
        self.assertIn("Requested sync of %d packages" % len(spphs),  notice)

    def test_do_copy_goes_async_if_canCopySynchronously_says_so(self):
        spph = self.factory.makeSourcePackagePublishingHistory()
        pocket = self.factory.getAnyPocket()
        view = self.makeView()
        dest_series = view.context
        archive = dest_series.distribution.main_archive
        view.canCopySynchronously = FakeMethod(result=False)
        view.do_copy(
            'selected_differences', [spph], archive, dest_series, pocket,
            False, check_permissions=False)
        jobs = list(getUtility(IPackageCopyJobSource).getActiveJobs(archive))
        self.assertNotEqual([], jobs)

    def test_do_copy_synchronously_checks_permissions(self):
        spph = self.factory.makeSourcePackagePublishingHistory()
        view = self.makeView()
        view.canCopySynchronously = FakeMethod(result=True)
        dest_series = view.context
        archive = dest_series.distribution.main_archive
        pocket = self.factory.getAnyPocket()
        view.do_copy(
            'selected_differences', [spph], archive, dest_series, pocket,
            False, check_permissions=True)
# XXX: Implement
        self.assertTrue(False)

    def test_do_copy_asynchronously_checks_permissions(self):
        spph = self.factory.makeSourcePackagePublishingHistory()
        view = self.makeView()
        view.canCopySynchronously = FakeMethod(result=False)
        dest_series = view.context
        archive = dest_series.distribution.main_archive
        pocket = self.factory.getAnyPocket()
        view.do_copy(
            'selected_differences', [spph], archive, dest_series, pocket,
            False, check_permissions=True)
# XXX: Implement
        self.assertTrue(False)
