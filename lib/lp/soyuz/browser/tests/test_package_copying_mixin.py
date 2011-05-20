# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `PackageCopyingMixin`."""

__metaclass__ = type

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.features.testing import FeatureFixture
from lp.services.propertycache import cachedproperty
from lp.soyuz.browser.archive import (
    compose_synchronous_copy_feedback,
    copy_asynchronously,
    copy_synchronously,
    FEATURE_FLAG_MAX_SYNCHRONOUS_SYNCS,
    name_pubs_with_versions,
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
from lp.testing import (
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.fakemethod import FakeMethod
from lp.testing.views import create_initialized_view


def find_spph_copy(archive, spph):
    """Find copy of `spph`'s package as copied into `archive`"""
    spr = spph.sourcepackagerelease
    return archive.getPublishedSources(
        name=spr.sourcepackagename.name, version=spr.version).one()


class FakeDistribution:
    def __init__(self):
        self.archive = FakeArchive()


class FakeDistroSeries:
    def __init__(self):
        self.distribution = FakeDistribution()


class FakeSPN:
    name = "spn-name"


class FakeSPR:
    def __init__(self):
        self.sourcepackagename = FakeSPN()
        self.version = "1.0"


class FakeArchive:
    def __init__(self, displayname="archive-name"):
        self.displayname = displayname


class FakeSPPH:
    def __init__(self, archive=None):
        if archive is None:
            archive = FakeArchive()
        self.sourcepackagerelease = FakeSPR()
        self.displayname = "spph-displayname"
        self.archive = archive


class TestPackageCopyingMixinLight(TestCase):
    """Test lightweight functions and methods.

    This test does not run in a layer and does not access the database.
    """

    unique_number = 1

    def getPocket(self):
        """Return an arbitrary `PackagePublishingPocket`."""
        return PackagePublishingPocket.SECURITY

    def getUniqueString(self):
        """Return an arbitrary string."""
        self.unique_number += 1
        return "string_%d_" % self.unique_number

    def test_canCopySynchronously_allows_small_synchronous_copies(self):
        # Small numbers of packages can be copied synchronously.
        packages = [self.getUniqueString() for counter in range(3)]
        self.assertTrue(PackageCopyingMixin().canCopySynchronously(packages))

    def test_canCopySynchronously_disallows_large_synchronous_copies(self):
        # Large numbers of packages must be copied asynchronously.
        packages = [self.getUniqueString() for counter in range(300)]
        self.assertFalse(PackageCopyingMixin().canCopySynchronously(packages))

    def test_partition_pubs_by_archive_maps_archives_to_pubs(self):
        # partition_pubs_by_archive returns a dict mapping each archive
        # to a list of SPPHs on that archive.
        spph = FakeSPPH()
        self.assertEqual(
            {spph.archive: [spph]}, partition_pubs_by_archive([spph]))

    def test_partition_pubs_by_archive_splits_by_archive(self):
        # partition_pubs_by_archive keeps SPPHs for different archives
        # separate.
        spphs = [FakeSPPH() for counter in xrange(2)]
        mapping = partition_pubs_by_archive(spphs)
        self.assertEqual(
            dict((spph.archive, [spph]) for spph in spphs), mapping)

    def test_partition_pubs_by_archive_clusters_by_archive(self):
        # partition_pubs_by_archive bundles SPPHs for the same archive
        # into a single dict entry.
        archive = FakeArchive()
        spphs = [FakeSPPH(archive=archive) for counter in xrange(2)]
        mapping = partition_pubs_by_archive(spphs)
        self.assertEqual([archive], mapping.keys())
        self.assertContentEqual(spphs, mapping[archive])

    def test_name_pubs_with_versions_lists_packages_and_versions(self):
        # name_pubs_with_versions returns a list of tuples of source
        # package name and source package version, one per SPPH.
        spph = FakeSPPH()
        spr = spph.sourcepackagerelease
        self.assertEqual(
            [(spr.sourcepackagename.name, spr.version)],
            name_pubs_with_versions([spph]))

    def test_render_cannotcopy_as_html_lists_errors(self):
        # render_cannotcopy_as_html includes a CannotCopy error message
        # into its HTML notice.
        message = self.getUniqueString()
        html_text = render_cannotcopy_as_html(CannotCopy(message)).escapedtext
        self.assertIn(message, html_text)

    def test_render_cannotcopy_as_html_escapes_error(self):
        # render_cannotcopy_as_html escapes error messages.
        message = "x<>y"
        html_text = render_cannotcopy_as_html(CannotCopy(message)).escapedtext
        self.assertNotIn(message, html_text)
        self.assertIn("x&lt;&gt;y", html_text)

    def test_compose_synchronous_copy_feedback_escapes_archive_name(self):
        # compose_synchronous_copy_feedback escapes archive displaynames.
        archive = FakeArchive(displayname="a&b")
        notice = compose_synchronous_copy_feedback(
            ["hi"], archive, dest_url="/")
        html_text = notice.escapedtext
        self.assertNotIn("a&b", html_text)
        self.assertIn("a&amp;b", html_text)

    def test_compose_synchronous_copy_feedback_escapes_package_names(self):
        # compose_synchronous_copy_feedback escapes package names.
        archive = FakeArchive()
        notice = compose_synchronous_copy_feedback(
            ["x<y"], archive, dest_url="/")
        html_text = notice.escapedtext
        self.assertNotIn("x<y", html_text)
        self.assertIn("x&lt;y", html_text)


class TestPackageCopyingMixinIntegration(TestCaseWithFactory):
    """Integration tests for `PackageCopyingMixin`."""

    layer = LaunchpadFunctionalLayer

    @cachedproperty
    def person(self):
        """Create a single person who gets blamed for everything.

        Creating SPPHs, Archives etc. in the factory creates lots of
        `Person`s, which turns out to be really slow.  Tests that don't
        care who's who can use this single person for all uninteresting
        Person fields.
        """
        return self.factory.makePerson()

    def makeDistribution(self):
        """Create a `Distribution`, but quickly by reusing a single Person."""
        return self.factory.makeDistribution(
            owner=self.person, registrant=self.person)

    def makeDistroSeries(self, previous_series=None):
        """Create a `DistroSeries`, but quickly by reusing a single Person."""
        return self.factory.makeDistroSeries(
            distribution=self.makeDistribution(),
            previous_series=previous_series,
            registrant=self.person)

    def makeSPPH(self):
        """Create a `SourcePackagePublishingHistory` quickly."""
        archive = self.factory.makeArchive(
            owner=self.person, distribution=self.makeDistribution())
        return self.factory.makeSourcePackagePublishingHistory(
            maintainer=self.person, creator=self.person, archive=archive)

    def makeDerivedSeries(self):
        """Create a derived `DistroSeries`, quickly."""
        series = self.makeDistroSeries(previous_series=self.makeDistroSeries())
        getUtility(ISourcePackageFormatSelectionSet).add(
            series, SourcePackageFormat.FORMAT_1_0)
        return series

    def makeView(self):
        """Create a `PackageCopyingMixin`-based view."""
        return create_initialized_view(
            self.makeDerivedSeries(), "+localpackagediffs")

    def getUploader(self, archive, spn):
        """Get person with upload rights for the given package and archive."""
        uploader = archive.owner
        removeSecurityProxy(archive).newPackageUploader(uploader, spn)
        return uploader

    def test_canCopySynchronously_obeys_feature_flag(self):
        packages = [self.getUniqueString() for counter in range(3)]
        mixin = PackageCopyingMixin()
        with FeatureFixture({FEATURE_FLAG_MAX_SYNCHRONOUS_SYNCS: 2}):
            can_copy_synchronously = mixin.canCopySynchronously(packages)
        self.assertFalse(can_copy_synchronously)

    def test_copy_synchronously_copies_packages(self):
        # copy_synchronously copies packages into the destination
        # archive.
        spph = self.makeSPPH()
        dest_series = self.makeDerivedSeries()
        archive = dest_series.distribution.main_archive
        pocket = self.factory.getAnyPocket()
        copy_synchronously(
            [spph], archive, dest_series, pocket, include_binaries=False,
            check_permissions=False)
        self.assertNotEqual(None, find_spph_copy(archive, spph))

    def test_copy_asynchronously_does_not_copy_packages(self):
        # copy_asynchronously does not copy packages into the destination
        # archive; that happens later, asynchronously.
        spph = self.makeSPPH()
        dest_series = self.makeDerivedSeries()
        archive = dest_series.distribution.main_archive
        pocket = self.factory.getAnyPocket()
        copy_asynchronously(
            [spph], archive, dest_series, pocket, include_binaries=False,
            check_permissions=False)
        self.assertEqual(None, find_spph_copy(archive, spph))

    def test_copy_synchronously_lists_packages(self):
        # copy_synchronously returns feedback that includes the names of
        # packages it copied.
        spph = self.makeSPPH()
        dest_series = self.makeDerivedSeries()
        pocket = self.factory.getAnyPocket()
        notice = copy_synchronously(
            [spph], dest_series.distribution.main_archive, dest_series,
            pocket, include_binaries=False,
            check_permissions=False).escapedtext
        self.assertIn(
            spph.sourcepackagerelease.sourcepackagename.name, notice)

    def test_copy_asynchronously_creates_copy_jobs(self):
        # copy_asynchronously creates PackageCopyJobs.
        spph = self.makeSPPH()
        dest_series = self.makeDerivedSeries()
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

    def test_do_copy_goes_async_if_canCopySynchronously_says_so(self):
        # The view opts for asynchronous copying if canCopySynchronously
        # returns False.  This creates PackageCopyJobs.
        spph = self.makeSPPH()
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

    def test_copy_synchronously_may_allow_copy(self):
        # In a normal working situation, copy_synchronously allows a
        # copy.
        spph = self.makeSPPH()
        pocket = PackagePublishingPocket.RELEASE
        dest_series = self.makeDerivedSeries()
        dest_archive = dest_series.main_archive
        spn = spph.sourcepackagerelease.sourcepackagename
        notification = copy_synchronously(
            [spph], dest_archive, dest_series, pocket, False,
            person=self.getUploader(dest_archive, spn))
        self.assertIn("Packages copied", notification.escapedtext)

    def test_copy_synchronously_checks_permissions(self):
        # Unless told not to, copy_synchronously does a permissions
        # check.
        spph = self.makeSPPH()
        pocket = self.factory.getAnyPocket()
        dest_series = self.makeDistroSeries()
        self.assertRaises(
            CannotCopy,
            copy_synchronously,
            [spph], dest_series.main_archive, dest_series, pocket, False)

    def test_copy_asynchronously_may_allow_copy(self):
        # In a normal working situation, copy_asynchronously allows a
        # copy.
        spph = self.makeSPPH()
        pocket = PackagePublishingPocket.RELEASE
        dest_series = self.makeDerivedSeries()
        dest_archive = dest_series.main_archive
        spn = spph.sourcepackagerelease.sourcepackagename
        notification = copy_asynchronously(
            [spph], dest_archive, dest_series, pocket, False,
            person=self.getUploader(dest_archive, spn))
        self.assertIn("Requested", notification.escapedtext)

    def test_copy_asynchronously_checks_permissions(self):
        # Unless told not to, copy_asynchronously does a permissions
        # check.
        spph = self.makeSPPH()
        pocket = self.factory.getAnyPocket()
        dest_series = self.makeDistroSeries()
        self.assertRaises(
            CannotCopy,
            copy_asynchronously,
            [spph], dest_series.main_archive, dest_series, pocket, False)
