# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for domination.py."""

__metaclass__ = type

import datetime

import apt_pkg
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
from lp.testing import TestCaseWithFactory


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


class TestGeneralizedPublication(TestCaseWithFactory):
    """Test publication generalization helpers."""

    layer = ZopelessDatabaseLayer

    def alterCreationDates(self, spphs, ages):
        """Set `datecreated` on each of `spphs` according to `ages`.

        :param spphs: Iterable of `SourcePackagePublishingHistory`.  Their
            respective creation dates will be offset by the respective ages
            found in `ages` (with the two being matched up in the same order).
        :param ages: Iterable of ages.  Must provide the same number of items
            as `spphs`.  Ages are `timedelta` objects that will be subtracted
            from the creation dates on the respective records in `spph`.
        """
        for spph, age in zip(spphs, ages):
            spph.datecreated -= age

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
        self.alterCreationDates(spphs, ages)

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
        self.alterCreationDates(spphs, ages)

        self.assertEqual(
            [spphs[2], spphs[0], spphs[1]],
            sorted(spphs, cmp=GeneralizedPublication().compare))


class TestDominatorMethods(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def makeDominator(self, publications):
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

    def test_dominateRemovedSourceVersions_dominates_publications(self):
        # dominateRemovedSourceVersions finds the publications for a
        # package and calls dominatePackage on them.
        pubs = make_spphs_for_versions(self.factory, ['0.1', '0.2', '0.3'])
        package_name = pubs[0].sourcepackagerelease.sourcepackagename.name

        self.makeDominator(pubs).dominateRemovedSourceVersions(
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

    def test_dominateRemovedSourceVersions_ignores_other_pockets(self):
        # dominateRemovedSourceVersions ignores publications in other
        # pockets than the one specified.
        pubs = make_spphs_for_versions(self.factory, ['2.3', '2.4'])
        package_name = pubs[0].sourcepackagerelease.sourcepackagename.name
        removeSecurityProxy(pubs[0]).pocket = PackagePublishingPocket.UPDATES
        removeSecurityProxy(pubs[1]).pocket = PackagePublishingPocket.PROPOSED
        self.makeDominator(pubs).dominateRemovedSourceVersions(
            pubs[0].distroseries, pubs[0].pocket, package_name, ['2.3'])
        self.assertEqual(PackagePublishingStatus.PUBLISHED, pubs[1].status)

    def test_dominateRemovedSourceVersions_ignores_other_packages(self):
        pubs = make_spphs_for_versions(self.factory, ['1.0', '1.1'])
        other_package_name = self.factory.makeSourcePackageName().name
        self.makeDominator(pubs).dominateRemovedSourceVersions(
            pubs[0].distroseries, pubs[0].pocket, other_package_name, ['1.1'])
        self.assertEqual(PackagePublishingStatus.PUBLISHED, pubs[0].status)
