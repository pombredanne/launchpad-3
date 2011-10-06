# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for domination.py."""

__metaclass__ = type

import datetime
from operator import attrgetter

import apt_pkg
from testtools.matchers import LessThan
from zope.security.proxy import removeSecurityProxy

from canonical.database.sqlbase import flush_database_updates
from canonical.testing.layers import ZopelessDatabaseLayer
from lp.archivepublisher.domination import (
    Dominator,
    GeneralizedPublication,
    STAY_OF_EXECUTION,
    )
from lp.archivepublisher.publishing import Publisher
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.services.log.logger import DevNullLogger
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.interfaces.publishing import ISourcePackagePublishingHistory
from lp.soyuz.tests.test_publishing import TestNativePublishingBase
from lp.testing import (
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.matchers import HasQueryCount


class TestDominator(TestNativePublishingBase):
    """Test Dominator class."""

    def createSourceAndBinaries(self, version, with_debug=False,
                                archive=None):
        """Create a source and binaries with the given version."""
        source = self.getPubSource(
            version=version, archive=archive,
            status=PackagePublishingStatus.PUBLISHED)
        binaries = self.getPubBinaries(
            pub_source=source, with_debug=with_debug,
            status=PackagePublishingStatus.PUBLISHED)
        return (source, binaries)

    def createSimpleDominationContext(self):
        """Create simple domination context.

        Creates source and binary publications for:

         * Dominated: foo_1.0 & foo-bin_1.0_i386
         * Dominant: foo_1.1 & foo-bin_1.1_i386

        Return the corresponding publication records as a 4-tuple:

         (dominant_source, dominant_binary, dominated_source,
          dominated_binary)

        Note that as an optimization the binaries list is already unpacked.
        """
        foo_10_source, foo_10_binaries = self.createSourceAndBinaries('1.0')
        foo_11_source, foo_11_binaries = self.createSourceAndBinaries('1.1')
        return (foo_11_source, foo_11_binaries[0],
                foo_10_source, foo_10_binaries[0])

    def dominateAndCheck(self, dominant, dominated, supersededby):
        generalization = GeneralizedPublication(
            is_source=ISourcePackagePublishingHistory.providedBy(dominant))
        dominator = Dominator(self.logger, self.ubuntutest.main_archive)

        # The _dominate* test methods require a dictionary where the
        # package name is the key. The key's value is a list of
        # source or binary packages representing dominant, the first element
        # and dominated, the subsequents.
        pubs = {'foo': [dominant, dominated]}

        dominator._dominatePublications(pubs, generalization)
        flush_database_updates()

        # The dominant version remains correctly published.
        self.checkPublication(dominant, PackagePublishingStatus.PUBLISHED)
        self.assertTrue(dominant.supersededby is None)
        self.assertTrue(dominant.datesuperseded is None)

        # The dominated version is correctly dominated.
        self.checkPublication(dominated, PackagePublishingStatus.SUPERSEDED)
        self.assertEqual(dominated.supersededby, supersededby)
        self.checkPastDate(dominated.datesuperseded)

    def testManualSourceDomination(self):
        """Test source domination procedure."""
        [dominant_source, dominant_binary, dominated_source,
         dominated_binary] = self.createSimpleDominationContext()

        self.dominateAndCheck(
            dominant_source, dominated_source,
            dominant_source.sourcepackagerelease)

    def testManualBinaryDomination(self):
        """Test binary domination procedure."""
        [dominant_source, dominant, dominated_source,
         dominated] = self.createSimpleDominationContext()

        self.dominateAndCheck(
            dominant, dominated, dominant.binarypackagerelease.build)

    def testJudgeAndDominate(self):
        """Verify that judgeAndDominate correctly dominates everything."""
        foo_10_source, foo_10_binaries = self.createSourceAndBinaries('1.0')
        foo_11_source, foo_11_binaries = self.createSourceAndBinaries('1.1')
        foo_12_source, foo_12_binaries = self.createSourceAndBinaries('1.2')

        dominator = Dominator(self.logger, foo_10_source.archive)
        dominator.judgeAndDominate(
            foo_10_source.distroseries, foo_10_source.pocket)

        self.checkPublications(
            [foo_12_source] + foo_12_binaries,
            PackagePublishingStatus.PUBLISHED)
        self.checkPublications(
            [foo_11_source] + foo_11_binaries,
            PackagePublishingStatus.SUPERSEDED)
        self.checkPublications(
            [foo_10_source] + foo_10_binaries,
            PackagePublishingStatus.SUPERSEDED)

    def testJudgeAndDominateWithDDEBs(self):
        """Verify that judgeAndDominate ignores DDEBs correctly.

        DDEBs are superseded by their corresponding DEB publications, so they
        are forbidden from superseding publications (an attempt would result
        in an AssertionError), and shouldn't be directly considered for
        superseding either.
        """
        ppa = self.factory.makeArchive()
        foo_10_source, foo_10_binaries = self.createSourceAndBinaries(
            '1.0', with_debug=True, archive=ppa)
        foo_11_source, foo_11_binaries = self.createSourceAndBinaries(
            '1.1', with_debug=True, archive=ppa)
        foo_12_source, foo_12_binaries = self.createSourceAndBinaries(
            '1.2', with_debug=True, archive=ppa)

        dominator = Dominator(self.logger, ppa)
        dominator.judgeAndDominate(
            foo_10_source.distroseries, foo_10_source.pocket)

        self.checkPublications(
            [foo_12_source] + foo_12_binaries,
            PackagePublishingStatus.PUBLISHED)
        self.checkPublications(
            [foo_11_source] + foo_11_binaries,
            PackagePublishingStatus.SUPERSEDED)
        self.checkPublications(
            [foo_10_source] + foo_10_binaries,
            PackagePublishingStatus.SUPERSEDED)

    def testEmptyDomination(self):
        """Domination asserts for not empty input list."""
        dominator = Dominator(self.logger, self.ubuntutest.main_archive)
        pubs = {'foo': []}
        # This isn't a really good exception. It should probably be
        # something more indicative of bad input.
        self.assertRaises(
            AssertionError,
            dominator._dominatePublications,
            pubs, GeneralizedPublication(True))


class TestDomination(TestNativePublishingBase):
    """Test overall domination procedure."""

    def testCarefulDomination(self):
        """Test the careful domination procedure.

        Check if it works on a development series.
        A SUPERSEDED, DELETED or OBSOLETE published source should
        have its scheduleddeletiondate set.
        """
        publisher = Publisher(
            self.logger, self.config, self.disk_pool,
            self.ubuntutest.main_archive)

        superseded_source = self.getPubSource(
            status=PackagePublishingStatus.SUPERSEDED)
        self.assertTrue(superseded_source.scheduleddeletiondate is None)
        deleted_source = self.getPubSource(
            status=PackagePublishingStatus.DELETED)
        self.assertTrue(deleted_source.scheduleddeletiondate is None)
        obsoleted_source = self.getPubSource(
            status=PackagePublishingStatus.OBSOLETE)
        self.assertTrue(obsoleted_source.scheduleddeletiondate is None)

        publisher.B_dominate(True)

        # The publishing records will be scheduled for removal.
        # DELETED and OBSOLETED publications are set to be deleted
        # immediately, whereas SUPERSEDED ones get a stay of execution
        # according to the configuration.
        self.checkPublication(
            deleted_source, PackagePublishingStatus.DELETED)
        self.checkPastDate(deleted_source.scheduleddeletiondate)

        self.checkPublication(
            obsoleted_source, PackagePublishingStatus.OBSOLETE)
        self.checkPastDate(deleted_source.scheduleddeletiondate)

        self.checkPublication(
            superseded_source, PackagePublishingStatus.SUPERSEDED)
        self.checkPastDate(
            superseded_source.scheduleddeletiondate,
            lag=datetime.timedelta(days=STAY_OF_EXECUTION))


class TestDominationOfObsoletedSeries(TestDomination):
    """Replay domination tests upon a OBSOLETED distroseries."""

    def setUp(self):
        TestDomination.setUp(self)
        self.ubuntutest['breezy-autotest'].status = (
            SeriesStatus.OBSOLETE)


def make_spphs_for_versions(factory, versions):
    """Create publication records for each of `versions`.

    They records are created in the same order in which they are specified.
    Make the order irregular to prove that version ordering is not a
    coincidence of object creation order etc.

    Versions may also be identical; each publication record will still have
    its own package release.
    """
    spn = factory.makeSourcePackageName()
    distroseries = factory.makeDistroSeries()
    pocket = factory.getAnyPocket()
    sprs = [
        factory.makeSourcePackageRelease(
            sourcepackagename=spn, version=version)
        for version in versions]
    return [
        factory.makeSourcePackagePublishingHistory(
            distroseries=distroseries, pocket=pocket,
            sourcepackagerelease=spr,
            status=PackagePublishingStatus.PUBLISHED)
        for spr in sprs]


def list_source_versions(spphs):
    """Extract the versions from `spphs` as a list, in the same order."""
    return [spph.sourcepackagerelease.version for spph in spphs]


def alter_creation_dates(spphs, ages):
    """Set `datecreated` on each of `spphs` according to `ages`.

    :param spphs: Iterable of `SourcePackagePublishingHistory`.  Their
        respective creation dates will be offset by the respective ages found
        in `ages` (with the two being matched up in the same order).
    :param ages: Iterable of ages.  Must provide the same number of items as
        `spphs`.  Ages are `timedelta` objects that will be subtracted from
        the creation dates on the respective records in `spph`.
    """
    for spph, age in zip(spphs, ages):
        spph.datecreated -= age


class TestGeneralizedPublication(TestCaseWithFactory):
    """Test publication generalization helpers."""

    layer = ZopelessDatabaseLayer

    def test_getPackageVersion_gets_source_version(self):
        spph = self.factory.makeSourcePackagePublishingHistory()
        self.assertEqual(
            spph.sourcepackagerelease.version,
            GeneralizedPublication(is_source=True).getPackageVersion(spph))

    def test_getPackageVersion_gets_binary_version(self):
        bpph = self.factory.makeBinaryPackagePublishingHistory()
        self.assertEqual(
            bpph.binarypackagerelease.version,
            GeneralizedPublication(is_source=False).getPackageVersion(bpph))

    def test_load_releases_loads_sourcepackagerelease(self):
        spph = self.factory.makeSourcePackagePublishingHistory()
        self.assertContentEqual(
            [spph.sourcepackagerelease],
            GeneralizedPublication(is_source=True).load_releases([spph]))

    def test_load_releases_loads_binarypackagerelease(self):
        bpph = self.factory.makeBinaryPackagePublishingHistory(
            binarypackagerelease=self.factory.makeBinaryPackageRelease())
        self.assertContentEqual(
            [bpph.binarypackagerelease],
            GeneralizedPublication(is_source=False).load_releases([bpph]))

    def test_compare_sorts_versions(self):
        versions = [
            '1.1v2',
            '1.1v1',
            '1.1v3',
            ]
        spphs = make_spphs_for_versions(self.factory, versions)
        sorted_spphs = sorted(spphs, cmp=GeneralizedPublication().compare)
        self.assertEqual(
            sorted(versions), list_source_versions(sorted_spphs))

    def test_compare_orders_versions_by_debian_rules(self):
        versions = [
            '1.1.0',
            '1.10',
            '1.1',
            '1.1ubuntu0',
            ]
        spphs = make_spphs_for_versions(self.factory, versions)

        debian_sorted_versions = sorted(versions, cmp=apt_pkg.VersionCompare)

        # Assumption: in this case, Debian version ordering is not the
        # same as alphabetical version ordering.
        self.assertNotEqual(sorted(versions), debian_sorted_versions)

        # The compare method produces the Debian ordering.
        sorted_spphs = sorted(spphs, cmp=GeneralizedPublication().compare)
        self.assertEqual(
            sorted(versions, cmp=apt_pkg.VersionCompare),
            list_source_versions(sorted_spphs))

    def test_compare_breaks_tie_with_creation_date(self):
        # When two publications are tied for comparison because they are
        # for the same package release, they are ordered by creation
        # date.
        distroseries = self.factory.makeDistroSeries()
        pocket = self.factory.getAnyPocket()
        spr = self.factory.makeSourcePackageRelease()
        ages = [
            datetime.timedelta(2),
            datetime.timedelta(1),
            datetime.timedelta(3),
            ]
        spphs = [
            self.factory.makeSourcePackagePublishingHistory(
                sourcepackagerelease=spr, distroseries=distroseries,
                pocket=pocket)
            for counter in xrange(len(ages))]
        alter_creation_dates(spphs, ages)

        self.assertEqual(
            [spphs[2], spphs[0], spphs[1]],
            sorted(spphs, cmp=GeneralizedPublication().compare))

    def test_compare_breaks_tie_for_releases_with_same_version(self):
        # When two publications are tied for comparison because they
        # belong to releases with the same version string, they are
        # ordered by creation date.
        version = "1.%d" % self.factory.getUniqueInteger()
        ages = [
            datetime.timedelta(2),
            datetime.timedelta(1),
            datetime.timedelta(3),
            ]
        distroseries = self.factory.makeDistroSeries()
        pocket = self.factory.getAnyPocket()
        spphs = [
            self.factory.makeSourcePackagePublishingHistory(
                distroseries=distroseries, pocket=pocket,
                sourcepackagerelease=self.factory.makeSourcePackageRelease(
                    version=version))
            for counter in xrange(len(ages))]
        alter_creation_dates(spphs, ages)

        self.assertEqual(
            [spphs[2], spphs[0], spphs[1]],
            sorted(spphs, cmp=GeneralizedPublication().compare))


def jumble(ordered_list):
    """Jumble the elements of `ordered_list` into a weird order.

    Ordering is very important in domination.  We jumble some of our lists to
    insure against "lucky coincidences" that might give our tests the right
    answers for the wrong reasons.
    """
    even = [
        item for offset, item in enumerate(ordered_list) if offset % 2 == 0]
    odd = [
        item for offset, item in enumerate(ordered_list) if offset % 2 != 0]
    return list(reversed(odd)) + even


class TestDominatorMethods(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def makeDominator(self, publications):
        """Create a `Dominator` suitable for `publications`."""
        if len(publications) == 0:
            archive = self.factory.makeArchive()
        else:
            archive = publications[0].archive
        return Dominator(DevNullLogger(), archive)

    def test_dominatePackage_survives_empty_publications_list(self):
        # Nothing explodes when dominatePackage is called with an empty
        # packages list.
        self.makeDominator([]).dominatePackage(
            [], [], GeneralizedPublication(True))
        # The test is that we get here without error.
        pass

    def test_dominatePackage_leaves_live_version_untouched(self):
        # dominatePackage does not supersede live versions.
        [pub] = make_spphs_for_versions(self.factory, ['3.1'])
        self.makeDominator([pub]).dominatePackage(
            [pub], ['3.1'], GeneralizedPublication(True))
        self.assertEqual(PackagePublishingStatus.PUBLISHED, pub.status)

    def test_dominatePackage_deletes_dead_version_without_successor(self):
        # dominatePackage marks non-live package versions without
        # superseding versions as deleted.
        [pub] = make_spphs_for_versions(self.factory, ['1.1'])
        self.makeDominator([pub]).dominatePackage(
            [pub], [], GeneralizedPublication(True))
        self.assertEqual(PackagePublishingStatus.DELETED, pub.status)

    def test_dominatePackage_supersedes_older_pub_with_newer_live_pub(self):
        # When marking a package as superseded, dominatePackage
        # designates a newer live version as the superseding version.
        pubs = make_spphs_for_versions(self.factory, ['1.0', '1.1'])
        self.makeDominator(pubs).dominatePackage(
            pubs, ['1.1'], GeneralizedPublication(True))
        self.assertEqual(PackagePublishingStatus.SUPERSEDED, pubs[0].status)
        self.assertEqual(pubs[1].sourcepackagerelease, pubs[0].supersededby)
        self.assertEqual(PackagePublishingStatus.PUBLISHED, pubs[1].status)

    def test_dominatePackage_only_supersedes_with_live_pub(self):
        # When marking a package as superseded, dominatePackage will
        # only pick a live version as the superseding one.
        pubs = make_spphs_for_versions(
            self.factory, ['1.0', '2.0', '3.0', '4.0'])
        self.makeDominator(pubs).dominatePackage(
            pubs, ['3.0'], GeneralizedPublication(True))
        self.assertEqual([
                pubs[2].sourcepackagerelease,
                pubs[2].sourcepackagerelease,
                None,
                None,
                ],
            [pub.supersededby for pub in pubs])

    def test_dominatePackage_supersedes_with_oldest_newer_live_pub(self):
        # When marking a package as superseded, dominatePackage picks
        # the oldest of the newer, live versions as the superseding one.
        pubs = make_spphs_for_versions(self.factory, ['2.7', '2.8', '2.9'])
        self.makeDominator(pubs).dominatePackage(
            pubs, ['2.8', '2.9'], GeneralizedPublication(True))
        self.assertEqual(pubs[1].sourcepackagerelease, pubs[0].supersededby)

    def test_dominatePackage_only_supersedes_with_newer_live_pub(self):
        # When marking a package as superseded, dominatePackage only
        # considers a newer version as the superseding one.
        pubs = make_spphs_for_versions(self.factory, ['0.1', '0.2'])
        self.makeDominator(pubs).dominatePackage(
            pubs, ['0.1'], GeneralizedPublication(True))
        self.assertEqual(None, pubs[1].supersededby)
        self.assertEqual(PackagePublishingStatus.DELETED, pubs[1].status)

    def test_dominatePackage_supersedes_replaced_pub_for_live_version(self):
        # Even if a publication record is for a live version, a newer
        # one for the same version supersedes it.
        spr = self.factory.makeSourcePackageRelease()
        series = self.factory.makeDistroSeries()
        pocket = PackagePublishingPocket.RELEASE
        pubs = [
            self.factory.makeSourcePackagePublishingHistory(
                archive=series.main_archive, distroseries=series,
                pocket=pocket, status=PackagePublishingStatus.PUBLISHED,
                sourcepackagerelease=spr)
            for counter in xrange(3)]
        alter_creation_dates(pubs, [
            datetime.timedelta(3),
            datetime.timedelta(2),
            datetime.timedelta(1),
            ])

        self.makeDominator(pubs).dominatePackage(
            pubs, [spr.version], GeneralizedPublication(True))
        self.assertEqual([
            PackagePublishingStatus.SUPERSEDED,
            PackagePublishingStatus.SUPERSEDED,
            PackagePublishingStatus.PUBLISHED,
            ],
            [pub.status for pub in pubs])
        self.assertEqual(
            [spr, spr, None], [pub.supersededby for pub in pubs])

    def test_dominatePackage_is_efficient(self):
        # dominatePackage avoids issuing too many queries.
        versions = ["1.%s" % revision for revision in xrange(5)]
        pubs = make_spphs_for_versions(self.factory, versions)
        with StormStatementRecorder() as recorder:
            self.makeDominator(pubs).dominatePackage(
                pubs, versions[2:-1],
                GeneralizedPublication(True))
        self.assertThat(recorder, HasQueryCount(LessThan(5)))

    def test_dominatePackage_advanced_scenario(self):
        # Put dominatePackage through its paces with complex combined
        # data.
        # This test should be redundant in theory (which in theory
        # equates practice but in practice does not).  If this fails,
        # don't just patch up the code or this test.  Create unit tests
        # that specifically cover the difference, then change the code
        # and/or adapt this test to return to harmony.
        series = self.factory.makeDistroSeries()
        package = self.factory.makeSourcePackageName()
        pocket = PackagePublishingPocket.RELEASE

        versions = ["1.%d" % number for number in xrange(4)]

        # We have one package releases for each version.
        relevant_releases = dict(
            (version, self.factory.makeSourcePackageRelease(
                sourcepackagename=package, version=version))
            for version in jumble(versions))

        # Each of those releases is subsequently published in
        # different components.
        components = jumble(
            [self.factory.makeComponent() for version in versions])

        # Map versions to lists of publications for that version, from
        # oldest to newest.  Each re-publishing into a different
        # component is meant to supersede publication into the previous
        # component.
        pubs_by_version = dict(
            (version, [
                self.factory.makeSourcePackagePublishingHistory(
                    archive=series.main_archive, distroseries=series,
                    pocket=pocket, status=PackagePublishingStatus.PUBLISHED,
                    sourcepackagerelease=relevant_releases[version],
                    component=component)
                for component in components])
            for version in jumble(versions))

        ages = jumble(
            [datetime.timedelta(age) for age in xrange(len(versions))])

        # Actually the "oldest to newest" order on the publications only
        # applies to their creation dates.  Their creation orders are
        # irrelevant.
        for pubs_list in pubs_by_version.itervalues():
            alter_creation_dates(pubs_list, ages)
            pubs_list.sort(key=attrgetter('datecreated'))

        live_versions = ["1.1", "1.2"]
        last_version_alive = sorted(live_versions)[-1]

        all_pubs = sum(pubs_by_version.itervalues(), [])
        Dominator(DevNullLogger(), series.main_archive).dominatePackage(
            all_pubs, live_versions, GeneralizedPublication(True))

        for version in reversed(versions):
            pubs = pubs_by_version[version]

            if version in live_versions:
                # Beware: loop-carried variable.  Used locally as well,
                # but tells later iterations what the highest-versioned
                # release so far was.  This is used in tracking
                # supersededby links.
                superseding_release = pubs[-1].sourcepackagerelease

            if version in live_versions:
                # The live versions' latest publications are Published,
                # their older ones Superseded.
                expected_status = (
                    [PackagePublishingStatus.SUPERSEDED] * (len(pubs) - 1) +
                    [PackagePublishingStatus.PUBLISHED])
                expected_supersededby = (
                    [superseding_release] * (len(pubs) - 1) + [None])
            elif version < last_version_alive:
                # The superseded versions older than the last live
                # version have all been superseded.
                expected_status = (
                    [PackagePublishingStatus.SUPERSEDED] * len(pubs))
                expected_supersededby = [superseding_release] * len(pubs)
            else:
                # Versions that are newer than any live release have
                # been deleted.
                expected_status = (
                    [PackagePublishingStatus.DELETED] * len(pubs))
                expected_supersededby = [None] * len(pubs)

            self.assertEqual(expected_status, [pub.status for pub in pubs])
            self.assertEqual(
                expected_supersededby, [pub.supersededby for pub in pubs])

    def test_dominateSourceVersions_dominates_publications(self):
        # dominateSourceVersions finds the publications for a package
        # and calls dominatePackage on them.
        pubs = make_spphs_for_versions(self.factory, ['0.1', '0.2', '0.3'])
        package_name = pubs[0].sourcepackagerelease.sourcepackagename.name

        self.makeDominator(pubs).dominateSourceVersions(
            pubs[0].distroseries, pubs[0].pocket, package_name, ['0.2'])
        self.assertEqual([
                PackagePublishingStatus.SUPERSEDED,
                PackagePublishingStatus.PUBLISHED,
                PackagePublishingStatus.DELETED,
                ],
            [pub.status for pub in pubs])
        self.assertEqual(
            [pubs[1].sourcepackagerelease, None, None],
            [pub.supersededby for pub in pubs])

    def test_dominateSourceVersions_ignores_other_pockets(self):
        # dominateSourceVersions ignores publications in other pockets
        # than the one specified.
        pubs = make_spphs_for_versions(self.factory, ['2.3', '2.4'])
        package_name = pubs[0].sourcepackagerelease.sourcepackagename.name
        removeSecurityProxy(pubs[0]).pocket = PackagePublishingPocket.UPDATES
        removeSecurityProxy(pubs[1]).pocket = PackagePublishingPocket.PROPOSED
        self.makeDominator(pubs).dominateSourceVersions(
            pubs[0].distroseries, pubs[0].pocket, package_name, ['2.3'])
        self.assertEqual(PackagePublishingStatus.PUBLISHED, pubs[1].status)

    def test_dominateSourceVersions_ignores_other_packages(self):
        pubs = make_spphs_for_versions(self.factory, ['1.0', '1.1'])
        other_package_name = self.factory.makeSourcePackageName().name
        self.makeDominator(pubs).dominateSourceVersions(
            pubs[0].distroseries, pubs[0].pocket, other_package_name, ['1.1'])
        self.assertEqual(PackagePublishingStatus.PUBLISHED, pubs[0].status)

    def test_findPublishedSourcePackageNames_finds_package(self):
        spph = self.factory.makeSourcePackagePublishingHistory(
            status=PackagePublishingStatus.PUBLISHED)
        dominator = self.makeDominator([spph])
        self.assertContentEqual(
            [(spph.sourcepackagerelease.sourcepackagename.name, 1)],
            dominator.findPublishedSourcePackageNames(
                spph.distroseries, spph.pocket))

    def test_findPublishedSourcePackageNames_ignores_other_states(self):
        series = self.factory.makeDistroSeries()
        pocket = PackagePublishingPocket.RELEASE
        spphs = dict(
            (status, self.factory.makeSourcePackagePublishingHistory(
                distroseries=series, archive=series.main_archive,
                pocket=pocket, status=status))
            for status in PackagePublishingStatus.items)
        published_spph = spphs[PackagePublishingStatus.PUBLISHED]
        dominator = self.makeDominator(spphs.values())
        self.assertContentEqual(
            [(published_spph.sourcepackagerelease.sourcepackagename.name, 1)],
            dominator.findPublishedSourcePackageNames(series, pocket))

    def test_findPublishedSourcePackageNames_ignores_other_archives(self):
        spph = self.factory.makeSourcePackagePublishingHistory(
            status=PackagePublishingStatus.PUBLISHED)
        dominator = self.makeDominator([spph])
        dominator.archive = self.factory.makeArchive()
        self.assertContentEqual(
            [],
            dominator.findPublishedSourcePackageNames(
                spph.distroseries, spph.pocket))

    def test_findPublishedSourcePackageNames_ignores_other_series(self):
        spph = self.factory.makeSourcePackagePublishingHistory(
            status=PackagePublishingStatus.PUBLISHED)
        distro = spph.distroseries.distribution
        other_series = self.factory.makeDistroSeries(distribution=distro)
        dominator = self.makeDominator([spph])
        self.assertContentEqual(
            [],
            dominator.findPublishedSourcePackageNames(
                other_series, spph.pocket))

    def test_findPublishedSourcePackageNames_ignores_other_pockets(self):
        spph = self.factory.makeSourcePackagePublishingHistory(
            status=PackagePublishingStatus.PUBLISHED,
            pocket=PackagePublishingPocket.RELEASE)
        dominator = self.makeDominator([spph])
        self.assertContentEqual(
            [],
            dominator.findPublishedSourcePackageNames(
                spph.distroseries, PackagePublishingPocket.SECURITY))

    def test_findPublishedSourcePackageNames_counts_published_SPPHs(self):
        series = self.factory.makeDistroSeries()
        pocket = PackagePublishingPocket.RELEASE
        spr = self.factory.makeSourcePackageRelease()
        spphs = [
            self.factory.makeSourcePackagePublishingHistory(
                distroseries=series, sourcepackagerelease=spr, pocket=pocket,
                status=PackagePublishingStatus.PUBLISHED)
            for counter in xrange(2)]
        dominator = self.makeDominator(spphs)
        self.assertContentEqual(
            [(spr.sourcepackagename.name, len(spphs))],
            dominator.findPublishedSourcePackageNames(series, pocket))

    def test_findPublishedSourcePackageNames_counts_no_other_state(self):
        series = self.factory.makeDistroSeries()
        pocket = PackagePublishingPocket.RELEASE
        spr = self.factory.makeSourcePackageRelease()
        spphs = [
            self.factory.makeSourcePackagePublishingHistory(
                distroseries=series, sourcepackagerelease=spr, pocket=pocket,
                status=status)
            for status in PackagePublishingStatus.items]
        dominator = self.makeDominator(spphs)
        self.assertContentEqual(
            [(spr.sourcepackagename.name, 1)],
            dominator.findPublishedSourcePackageNames(series, pocket))

    def test_findPublishedSPPHs_finds_published_SPPH(self):
        spph = self.factory.makeSourcePackagePublishingHistory(
            status=PackagePublishingStatus.PUBLISHED)
        package_name = spph.sourcepackagerelease.sourcepackagename.name
        dominator = self.makeDominator([spph])
        self.assertContentEqual(
            [spph],
            dominator.findPublishedSPPHs(
                spph.distroseries, spph.pocket, package_name))

    def test_findPublishedSPPHs_ignores_other_states(self):
        series = self.factory.makeDistroSeries()
        package = self.factory.makeSourcePackageName()
        pocket = PackagePublishingPocket.RELEASE
        spphs = dict(
            (status, self.factory.makeSourcePackagePublishingHistory(
                distroseries=series, archive=series.main_archive,
                pocket=pocket, status=status,
                sourcepackagerelease=self.factory.makeSourcePackageRelease(
                    sourcepackagename=package)))
            for status in PackagePublishingStatus.items)
        dominator = self.makeDominator(spphs.values())
        self.assertContentEqual(
            [spphs[PackagePublishingStatus.PUBLISHED]],
            dominator.findPublishedSPPHs(series, pocket, package.name))

    def test_findPublishedSPPHs_ignores_other_archives(self):
        spph = self.factory.makeSourcePackagePublishingHistory(
            status=PackagePublishingStatus.PUBLISHED)
        package = spph.sourcepackagerelease.sourcepackagename
        dominator = self.makeDominator([spph])
        dominator.archive = self.factory.makeArchive()
        self.assertContentEqual(
            [],
            dominator.findPublishedSPPHs(
                spph.distroseries, spph.pocket, package.name))

    def test_findPublishedSPPHs_ignores_other_series(self):
        spph = self.factory.makeSourcePackagePublishingHistory(
            status=PackagePublishingStatus.PUBLISHED)
        distro = spph.distroseries.distribution
        package = spph.sourcepackagerelease.sourcepackagename
        other_series = self.factory.makeDistroSeries(distribution=distro)
        dominator = self.makeDominator([spph])
        self.assertContentEqual(
            [],
            dominator.findPublishedSPPHs(
                other_series, spph.pocket, package.name))

    def test_findPublishedSPPHs_ignores_other_pockets(self):
        spph = self.factory.makeSourcePackagePublishingHistory(
            status=PackagePublishingStatus.PUBLISHED,
            pocket=PackagePublishingPocket.RELEASE)
        package = spph.sourcepackagerelease.sourcepackagename
        dominator = self.makeDominator([spph])
        self.assertContentEqual(
            [],
            dominator.findPublishedSPPHs(
                spph.distroseries, PackagePublishingPocket.SECURITY,
                package.name))

    def test_findPublishedSPPHs_ignores_other_packages(self):
        spph = self.factory.makeSourcePackagePublishingHistory(
            status=PackagePublishingStatus.PUBLISHED)
        other_package = self.factory.makeSourcePackageName()
        dominator = self.makeDominator([spph])
        self.assertContentEqual(
            [],
            dominator.findPublishedSPPHs(
                spph.distroseries, spph.pocket, other_package.name))
