# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the populate-distroseriesdiff script."""

__metaclass__ = type

from storm.store import Store
import transaction

from canonical.database.sqlbase import (
    cursor,
    quote,
    )
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    ZopelessDatabaseLayer,
    )
from lp.registry.enum import (
    DistroSeriesDifferenceStatus,
    DistroSeriesDifferenceType,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.model.distroseriesdifference import DistroSeriesDifference
from lp.registry.scripts.populate_distroseriesdiff import (
    BaseVersionFixer,
    compose_sql_difference_type,
    compose_sql_find_latest_source_package_releases,
    compose_sql_find_differences,
    compose_sql_populate_distroseriesdiff,
    find_derived_series,
    populate_distroseriesdiff,
    PopulateDistroSeriesDiff,
    )
from lp.services.log.logger import (
    BufferLogger,
    DevNullLogger,
    )
from lp.soyuz.interfaces.publishing import (
    active_publishing_status,
    inactive_publishing_status,
    )
from lp.soyuz.model.archive import Archive
from lp.soyuz.enums import ArchivePurpose
from lp.testing import (
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.fakemethod import FakeMethod


class FactoryHelper:
    """Some helper methods for making stuff that only make sense here."""

    def getArchive(self, distribution, purpose):
        """Get an existing `Archive`, or create one."""
        archive = Store.of(distribution).find(
            Archive,
            Archive.distribution == distribution,
            Archive.purpose == purpose).any()
        if archive is not None:
            return archive
        return self.factory.makeArchive(
            distribution=distribution, purpose=purpose)

    def makeSPPH(self, distroseries=None, archive_purpose=None,
                 pocket=PackagePublishingPocket.RELEASE, status=None,
                 sourcepackagerelease=None):
        """Create a `SourcePackagePublishingHistory` for derivation.

        Has slightly different defaults from the `LaunchpadObjectFactory`
        method for this, so that the SPPH will be picked up as a
        `DistroSeriesDifference`.
        """
        if distroseries is None:
            distroseries = self.factory.makeDistroSeries()

        if archive_purpose is None:
            archive = None
        else:
            archive = self.getArchive(
                distroseries.distribution, archive_purpose)

        return self.factory.makeSourcePackagePublishingHistory(
            pocket=pocket, distroseries=distroseries, archive=archive,
            status=status, sourcepackagerelease=sourcepackagerelease)

    def makeDerivedDistroSeries(self):
        """Create a `DistroSeries` that's derived from another distro."""
        return self.factory.makeDistroSeries(
            parent_series=self.factory.makeDistroSeries())

    def getDistroSeriesDiff(self, distroseries):
        """Find the `DistroSeriesDifference` records for `distroseries`."""
        return Store.of(distroseries).find(
            DistroSeriesDifference,
            DistroSeriesDifference.derived_series == distroseries)


class TestFindLatestSourcePackageReleases(TestCaseWithFactory, FactoryHelper):
    """Test finding of latest `SourcePackageRelease`s for a series' packages.
    """

    layer = ZopelessDatabaseLayer

    def getExpectedResultFor(self, spph):
        """Compose what the query should return for `spph`.

        :param spph: A `SourcePackagePublishingHistory`.
        :return: The tuple of data that we'd expect the latest-spr query
            to return for `spph`.
        """
        spr = spph.sourcepackagerelease
        return (spr.sourcepackagenameID, spr.id, spr.version)

    def test_baseline(self):
        distroseries = self.factory.makeDistroSeries()
        query = compose_sql_find_latest_source_package_releases(distroseries)
        self.assertIsInstance(query, basestring)

    def test_finds_nothing_for_empty_distroseries(self):
        distroseries = self.factory.makeDistroSeries()
        query = compose_sql_find_latest_source_package_releases(distroseries)
        self.assertContentEqual([], Store.of(distroseries).execute(query))

    def test_finds_published_sourcepackagerelease(self):
        spph = self.makeSPPH()
        query = compose_sql_find_latest_source_package_releases(
            spph.distroseries)
        self.assertEqual(1, Store.of(spph).execute(query).rowcount)

    def test_selects_sourcepackagename_sourcepackagerelease_version(self):
        spph = self.makeSPPH()
        spr = spph.sourcepackagerelease
        query = compose_sql_find_latest_source_package_releases(
            spph.distroseries)
        self.assertContentEqual(
            [self.getExpectedResultFor(spph)], Store.of(spph).execute(query))

    def test_does_not_find_publication_from_other_series(self):
        spph = self.makeSPPH()
        query = compose_sql_find_latest_source_package_releases(
            self.factory.makeDistroSeries())
        self.assertEqual(0, Store.of(spph).execute(query).rowcount)

    def test_does_not_find_publication_outside_primary_archive(self):
        distroseries = self.factory.makeDistroSeries()
        spphs = dict(
            (purpose, self.makeSPPH(
                distroseries=distroseries, archive_purpose=purpose))
            for purpose in ArchivePurpose.items)
        primary_spr = spphs[ArchivePurpose.PRIMARY]
        query = compose_sql_find_latest_source_package_releases(distroseries)
        self.assertContentEqual(
            [self.getExpectedResultFor(spphs[ArchivePurpose.PRIMARY])],
            Store.of(distroseries).execute(query))

    def test_does_not_find_publication_outside_release_pocket(self):
        distroseries = self.factory.makeDistroSeries()
        spphs = dict(
            (pocket, self.makeSPPH(distroseries=distroseries, pocket=pocket))
            for pocket in PackagePublishingPocket.items)
        release_spph = spphs[PackagePublishingPocket.RELEASE]
        query = compose_sql_find_latest_source_package_releases(distroseries)
        self.assertContentEqual(
            [self.getExpectedResultFor(release_spph)],
            Store.of(distroseries).execute(query))

    def test_finds_active_publication(self):
        distroseries = self.factory.makeDistroSeries()
        spphs = dict(
            (status, self.makeSPPH(distroseries=distroseries, status=status))
            for status in active_publishing_status)
        query = compose_sql_find_latest_source_package_releases(distroseries)
        self.assertContentEqual(
            [self.getExpectedResultFor(spph) for spph in spphs.itervalues()],
            Store.of(distroseries).execute(query))

    def test_does_not_find_inactive_publication(self):
        distroseries = self.factory.makeDistroSeries()
        spphs = dict(
            (status, self.makeSPPH(distroseries=distroseries, status=status))
            for status in inactive_publishing_status)
        query = compose_sql_find_latest_source_package_releases(distroseries)
        self.assertContentEqual([], Store.of(distroseries).execute(query))

    def test_finds_only_latest_publication_for_release(self):
        distroseries = self.factory.makeDistroSeries()
        spr = self.factory.makeSourcePackageRelease(distroseries=distroseries)
        spphs = [
            self.makeSPPH(distroseries=distroseries, sourcepackagerelease=spr)
            for counter in xrange(5)]
        query = compose_sql_find_latest_source_package_releases(distroseries)
        self.assertContentEqual(
            [self.getExpectedResultFor(spphs[-1])],
            Store.of(distroseries).execute(query))

    def test_finds_only_last_published_release_for_package(self):
        distroseries = self.factory.makeDistroSeries()
        spn = self.factory.makeSourcePackageName()
        sprs = [
            self.factory.makeSourcePackageRelease(
                sourcepackagename=spn, distroseries=distroseries)
            for counter in xrange(5)]
        spphs = [
            self.makeSPPH(distroseries=distroseries, sourcepackagerelease=spr)
            for spr in reversed(sprs)]
        query = compose_sql_find_latest_source_package_releases(distroseries)
        self.assertContentEqual(
            [self.getExpectedResultFor(spphs[-1])],
            Store.of(distroseries).execute(query))


class TestFindDifferences(TestCaseWithFactory, FactoryHelper):
    """Test the finding of differences between a distroseries and parent."""

    layer = ZopelessDatabaseLayer

    def test_baseline(self):
        query = compose_sql_find_differences(self.makeDerivedDistroSeries())
        self.assertIsInstance(query, basestring)

    def test_finds_nothing_for_empty_distroseries(self):
        distroseries = self.makeDerivedDistroSeries()
        query = compose_sql_find_differences(distroseries)
        self.assertContentEqual([], Store.of(distroseries).execute(query))

    def test_does_not_find_grandparents_packages(self):
        parent = self.makeDerivedDistroSeries()
        distroseries = self.factory.makeDistroSeries(parent_series=parent)
        self.makeSPPH(distroseries=parent.parent_series)
        query = compose_sql_find_differences(distroseries)
        self.assertContentEqual([], Store.of(distroseries).execute(query))

    def test_does_not_find_identical_releases(self):
        distroseries = self.makeDerivedDistroSeries()
        spr = self.factory.makeSourcePackageRelease()
        self.makeSPPH(
            distroseries=distroseries.parent_series, sourcepackagerelease=spr)
        self.makeSPPH(
            distroseries=distroseries, sourcepackagerelease=spr)
        query = compose_sql_find_differences(distroseries)
        self.assertContentEqual([], Store.of(distroseries).execute(query))

    def test_finds_release_missing_in_derived_series(self):
        distroseries = self.makeDerivedDistroSeries()
        spph = self.makeSPPH(distroseries=distroseries.parent_series)
        query = compose_sql_find_differences(distroseries)
        self.assertContentEqual(
            [(
                spph.sourcepackagerelease.sourcepackagenameID,
                None,
                spph.sourcepackagerelease.version,
            )],
            Store.of(distroseries).execute(query))

    def test_finds_release_unique_to_derived_series(self):
        distroseries = self.makeDerivedDistroSeries()
        spph = self.makeSPPH(distroseries=distroseries)
        query = compose_sql_find_differences(distroseries)
        self.assertContentEqual(
            [(
                spph.sourcepackagerelease.sourcepackagenameID,
                spph.sourcepackagerelease.version,
                None,
            )],
            Store.of(distroseries).execute(query))

    def test_does_not_conflate_releases_of_different_packages(self):
        distroseries = self.makeDerivedDistroSeries()
        parent_spph = self.makeSPPH(distroseries=distroseries.parent_series)
        derived_spph = self.makeSPPH(distroseries=distroseries)
        query = compose_sql_find_differences(distroseries)
        self.assertEqual(2, Store.of(distroseries).execute(query).rowcount)
        self.assertContentEqual([(
                parent_spph.sourcepackagerelease.sourcepackagenameID,
                None,
                parent_spph.sourcepackagerelease.version,
            ), (
                derived_spph.sourcepackagerelease.sourcepackagenameID,
                derived_spph.sourcepackagerelease.version,
                None,
            )],
            Store.of(distroseries).execute(query))

    def test_finds_different_releases_of_same_package(self):
        distroseries = self.makeDerivedDistroSeries()
        parent_series = distroseries.parent_series
        spn = self.factory.makeSourcePackageName()
        parent_spph = self.makeSPPH(
            distroseries=parent_series,
            sourcepackagerelease=self.factory.makeSourcePackageRelease(
                distroseries=parent_series, sourcepackagename=spn))
        derived_spph = self.makeSPPH(
            distroseries=distroseries,
            sourcepackagerelease=self.factory.makeSourcePackageRelease(
                distroseries=distroseries, sourcepackagename=spn))
        query = compose_sql_find_differences(distroseries)
        self.assertContentEqual(
            [(
                parent_spph.sourcepackagerelease.sourcepackagenameID,
                derived_spph.sourcepackagerelease.version,
                parent_spph.sourcepackagerelease.version,
            )],
            Store.of(distroseries).execute(query))

    def test_finds_newer_release_even_when_same_release_also_exists(self):
        derived_series = self.makeDerivedDistroSeries()
        parent_series = derived_series.parent_series
        spn = self.factory.makeSourcePackageName()
        shared_spr = self.factory.makeSourcePackageRelease(
            distroseries=parent_series, sourcepackagename=spn)
        parent_spph = self.makeSPPH(
            distroseries=parent_series,
            sourcepackagerelease=shared_spr)
        derived_spph = self.makeSPPH(
            distroseries=derived_series,
            sourcepackagerelease=shared_spr)
        newer_spr = self.factory.makeSourcePackageRelease(
            distroseries=derived_series, sourcepackagename=spn)
        self.makeSPPH(
            distroseries=derived_series, sourcepackagerelease=newer_spr)
        query = compose_sql_find_differences(derived_series)
        self.assertContentEqual(
            [(
                parent_spph.sourcepackagerelease.sourcepackagenameID,
                newer_spr.version,
                shared_spr.version,
            )],
            Store.of(derived_series).execute(query))


class TestDifferenceTypeExpression(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def selectDifferenceType(self, parent_version=None, derived_version=None):
        """Execute the SQL expression to compute `DistroSeriesDifferenceType`.

        :param parent_version: The parent series' last released version
            of a package, if any.
        :param derived_version: The derived series' last released
            version of the same package, if any.
        :return: A numeric `DistroSeriesDifferenceType` value.
        """
        query = """
            SELECT %s FROM (
                SELECT %s AS source_version, %s AS parent_source_version
            ) AS input""" % (
            compose_sql_difference_type(),
            quote(derived_version),
            quote(parent_version),
            )
        cur = cursor()
        cur.execute(query)
        result = cur.fetchall()
        self.assertEqual(1, len(result))
        self.assertEqual(1, len(result[0]))
        return result[0][0]

    def test_baseline(self):
        query = compose_sql_difference_type()
        self.assertIsInstance(query, basestring)

    def test_no_parent_version_means_unique_to_derived_series(self):
        expected = DistroSeriesDifferenceType.UNIQUE_TO_DERIVED_SERIES
        self.assertEqual(
            expected.value, self.selectDifferenceType(derived_version=1))

    def test_no_derived_version_means_missing_in_derived_series(self):
        expected = DistroSeriesDifferenceType.MISSING_FROM_DERIVED_SERIES
        self.assertEqual(
            expected.value, self.selectDifferenceType(parent_version=1))

    def test_two_versions_means_different_versions(self):
        expected = DistroSeriesDifferenceType.DIFFERENT_VERSIONS
        self.assertEqual(
            expected.value,
            self.selectDifferenceType(parent_version=1, derived_version=2))


class TestFindDerivedSeries(TestCaseWithFactory, FactoryHelper):
    """Test finding of all derived `DistroSeries`."""

    layer = ZopelessDatabaseLayer

    def test_does_not_find_underived_distroseries(self):
        distroseries = self.factory.makeDistroSeries()
        self.assertNotIn(distroseries, find_derived_series())

    def test_finds_derived_distroseries(self):
        self.assertIn(self.makeDerivedDistroSeries(), find_derived_series())

    def test_ignores_parent_within_same_distro(self):
        parent_series = self.factory.makeDistroSeries()
        derived_series = self.factory.makeDistroSeries(
            distribution=parent_series.distribution,
            parent_series=parent_series)
        self.assertNotIn(derived_series, find_derived_series())


class TestPopulateDistroSeriesDiff(TestCaseWithFactory, FactoryHelper):
    """Test `populate_distroseriesdiff`."""

    layer = LaunchpadFunctionalLayer

    def test_baseline(self):
        distroseries = self.factory.makeDistroSeries()
        query = compose_sql_populate_distroseriesdiff(distroseries, "tmp")
        self.assertIsInstance(query, basestring)

    def test_creates_distroseriesdifference(self):
        distroseries = self.makeDerivedDistroSeries()
        spph = self.makeSPPH(distroseries=distroseries)
        populate_distroseriesdiff(DevNullLogger(), distroseries)
        store = Store.of(distroseries)
        dsd = self.getDistroSeriesDiff(distroseries).one()
        spr = spph.sourcepackagerelease
        self.assertEqual(spr.sourcepackagename, dsd.source_package_name)
        self.assertEqual(
            DistroSeriesDifferenceStatus.NEEDS_ATTENTION, dsd.status)

    def test_does_not_overwrite_distroseriesdifference(self):
        distroseries = self.makeDerivedDistroSeries()
        changelog = self.factory.makeChangelog(versions=['3.1', '3.141'])
        parent_changelog = self.factory.makeChangelog(
            versions=['3.1', '3.14'])
        transaction.commit() # Yay, librarian.
        existing_versions = {
            'base': '3.1',
            'parent': '3.14',
            'derived': '3.141',
        }
        changelogs = {
            'derived': changelog,
            'parent': parent_changelog,
        }
        spph = self.makeSPPH(distroseries=distroseries)
        spr = spph.sourcepackagerelease
        self.factory.makeDistroSeriesDifference(
            derived_series=distroseries,
            source_package_name_str=spr.sourcepackagename.name,
            versions=existing_versions, changelogs=changelogs)
        dsd = self.getDistroSeriesDiff(distroseries).one()
        self.assertEqual(existing_versions['base'], dsd.base_version)
        self.assertEqual(
            existing_versions['parent'], dsd.parent_source_version)
        self.assertEqual(existing_versions['derived'], dsd.source_version)


class FakeDSD:
    _updateBaseVersion = FakeMethod()


class TestBaseVersionFixer(TestCase):
    """Test the poignant parts of `BaseVersionFixer`."""

    def makeFixer(self, ids):
        fixer = BaseVersionFixer(DevNullLogger(), None, FakeMethod(), ids)
        fixer._getBatch = FakeMethod()
        return fixer

    def test_isDone_is_done_when_ids_is_empty(self):
        self.assertTrue(self.makeFixer([]).isDone())

    def test_isDone_is_not_done_until_ids_is_empty(self):
        self.assertFalse(self.makeFixer([1]).isDone())

    def test_cutChunk_one_cuts_exactly_one(self):
        fixer = self.makeFixer(range(3))
        chunk = fixer._cutChunk(1)
        self.assertEqual([0], chunk)
        self.assertEqual(3 - 1, len(fixer.ids))

    def test_cutChunk_over_remaining_size_completes_loop(self):
        fixer = self.makeFixer(range(3))
        chunk = fixer._cutChunk(100)
        self.assertContentEqual(range(3), chunk)
        self.assertEqual([], fixer.ids)

    def test_updatesBaseVersion(self):
        fake_dsd = FakeDSD()
        fixer = self.makeFixer([fake_dsd])
        fixer._getBatch.result = fixer.ids
        fixer(1)
        self.assertNotEqual(0, fake_dsd._updateBaseVersion.call_count)

    def test_loop_commits(self):
        fixer = self.makeFixer([FakeDSD()])
        fixer._getBatch = FakeMethod(result=fixer.ids)
        fixer(1)
        self.assertNotEqual(0, fixer.commit.call_count)


class TestPopulateDistroSeriesDiffScript(TestCaseWithFactory, FactoryHelper):
    """Test the `populate-distroseriesdiff` script."""

    layer = DatabaseFunctionalLayer

    def makeScript(self, test_args):
        script = PopulateDistroSeriesDiff(test_args=test_args)
        script.logger = DevNullLogger()
        return script

    def test_finds_distroseries(self):
        spph = self.makeSPPH(distroseries=self.makeDerivedDistroSeries())
        script = self.makeScript([
            '--distribution', spph.distroseries.distribution.name,
            '--series', spph.distroseries.name,
            ])
        self.assertEqual([spph.distroseries], script.getDistroSeries())

    def test_finds_all_distroseries(self):
        spphs = [
            self.makeSPPH(self.makeDerivedDistroSeries())
            for counter in xrange(2)]
        script = self.makeScript(['--all'])
        distroseries = script.getDistroSeries()
        for spph in spphs:
            self.assertIn(spph.distroseries, distroseries)

    def test_populates_for_distroseries(self):
        spph = self.makeSPPH(distroseries=self.makeDerivedDistroSeries())
        script = self.makeScript([
            '--distribution', spph.distroseries.distribution.name,
            '--series', spph.distroseries.name,
            ])
        script.main()
        self.assertNotEqual(
            0, self.getDistroSeriesDiff(spph.distroseries).count())

    def test_commits_changes(self):
        spph = self.makeSPPH(distroseries=self.makeDerivedDistroSeries())
        script = self.makeScript([
            '--distribution', spph.distroseries.distribution.name,
            '--series', spph.distroseries.name,
            ])
        script.main()
        transaction.abort()
        # The changes are still in the database despite the abort,
        # because the script already committed them.
        self.assertNotEqual(
            0, self.getDistroSeriesDiff(spph.distroseries).count())

    def test_dry_run_goes_through_the_motions(self):
        spph = self.makeSPPH(distroseries=self.makeDerivedDistroSeries())
        script = self.makeScript(['--all', '--dry-run'])
        script.processDistroSeries = FakeMethod
        script.main()
        self.assertNotEqual(0, script.processDistroSeries.call_count)

    def test_dry_run_does_not_commit_changes(self):
        spph = self.makeSPPH(distroseries=self.makeDerivedDistroSeries())
        transaction.commit()
        script = self.makeScript([
            '--distribution', spph.distroseries.distribution.name,
            '--series', spph.distroseries.name,
            '--dry-run',
            ])
        script.main()
        self.assertContentEqual(
            [], self.getDistroSeriesDiff(spph.distroseries))

    def test_list(self):
        spph = self.makeSPPH(distroseries=self.makeDerivedDistroSeries())
        script = self.makeScript(['--list'])
        script.logger = BufferLogger()
        script.main()
        expected_series_name = "%s %s" % (
            spph.distroseries.distribution.name, spph.distroseries.name)
        self.assertIn(expected_series_name, script.logger.getLogBuffer())

    def test_calls_fixBaseVersions(self):
        distroseries = self.makeDerivedDistroSeries()
        self.makeSPPH(distroseries=distroseries)
        script = self.makeScript([
            '--distribution', distroseries.distribution.name,
            '--series', distroseries.name,
            ])
        script.fixBaseVersions = FakeMethod()
        script.main()
        self.assertEqual(
            [((distroseries,), {})], script.fixBaseVersions.calls)

    def test_fixes_base_versions(self):
        distroseries = self.makeDerivedDistroSeries()
        package = self.factory.makeSourcePackageName()
        derived_spr = self.factory.makeSourcePackageRelease(
            distroseries=distroseries, sourcepackagename=package)
        self.makeSPPH(
            distroseries=distroseries,
            sourcepackagerelease=derived_spr)
        parent_spr = self.factory.makeSourcePackageRelease(
            distroseries=distroseries.parent_series,
            sourcepackagename=package)
        self.makeSPPH(
            distroseries=distroseries.parent_series,
            sourcepackagerelease=parent_spr)
        script = self.makeScript([
            '--distribution', distroseries.distribution.name,
            '--series', distroseries.name,
            ])
        script.main()
        dsd = self.getDistroSeriesDiff(distroseries)[0]
        dsd._updateBaseVersion = FakeMethod()
        script.fixBaseVersions(distroseries)
        self.assertEqual(1, dsd._updateBaseVersion.call_count)
