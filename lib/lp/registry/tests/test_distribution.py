# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Distribution."""

__metaclass__ = type

from zope.security.proxy import removeSecurityProxy

from lazr.lifecycle.snapshot import Snapshot
from lp.registry.tests.test_distroseries import (
    TestDistroSeriesCurrentSourceReleases)
from lp.app.enums import ServiceUsage
from lp.registry.interfaces.distroseries import NoSuchDistroSeries
from lp.registry.interfaces.series import SeriesStatus
from lp.registry.interfaces.distribution import IDistribution

from lp.soyuz.interfaces.distributionsourcepackagerelease import (
    IDistributionSourcePackageRelease)
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from canonical.testing.layers import (
    DatabaseFunctionalLayer, LaunchpadFunctionalLayer)


class TestDistributionUsageEnums(TestCaseWithFactory):
    """Tests the usage enums for the distribution."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestDistributionUsageEnums, self).setUp()
        self.distribution = self.factory.makeDistribution()

    def test_answers_usage_no_data(self):
        # By default, we don't know anything about a distribution
        self.assertEqual(ServiceUsage.UNKNOWN, self.distribution.answers_usage)

    def test_answers_usage_using_bool(self):
        # If the old bool says they use Launchpad, return LAUNCHPAD
        # if the ServiceUsage is unknown.
        login_person(self.distribution.owner)
        self.distribution.official_answers = True
        self.assertEqual(ServiceUsage.LAUNCHPAD, self.distribution.answers_usage)

    def test_answers_usage_with_enum_data(self):
        # If the enum has something other than UNKNOWN as its status,
        # use that.
        login_person(self.distribution.owner)
        self.distribution.answers_usage = ServiceUsage.EXTERNAL
        self.assertEqual(ServiceUsage.EXTERNAL, self.distribution.answers_usage)

    def test_codehosting_usage(self):
        # Only test get for codehosting; this has no setter because the
        # state is derived from other data.
        distribution = self.factory.makeDistribution()
        self.assertEqual(ServiceUsage.UNKNOWN, distribution.codehosting_usage)

    def test_translations_usage_no_data(self):
        # By default, we don't know anything about a distribution
        self.assertEqual(
            ServiceUsage.UNKNOWN,
            self.distribution.translations_usage)

    def test_translations_usage_using_bool(self):
        # If the old bool says they use Launchpad, return LAUNCHPAD
        # if the ServiceUsage is unknown.
        login_person(self.distribution.owner)
        self.distribution.official_rosetta = True
        self.assertEqual(
            ServiceUsage.LAUNCHPAD,
            self.distribution.translations_usage)

    def test_translations_usage_with_enum_data(self):
        # If the enum has something other than UNKNOWN as its status,
        # use that.
        login_person(self.distribution.owner)
        self.distribution.translations_usage = ServiceUsage.EXTERNAL
        self.assertEqual(
            ServiceUsage.EXTERNAL,
            self.distribution.translations_usage)

    def test_bug_tracking_usage(self):
        # Only test get for bug_tracking; this has no setter because the
        # state is derived from other data.
        distribution = self.factory.makeDistribution()
        self.assertEqual(ServiceUsage.UNKNOWN, distribution.bug_tracking_usage)

    def test_blueprints_usage_no_data(self):
        # By default, we don't know anything about a distribution
        self.assertEqual(ServiceUsage.UNKNOWN, self.distribution.blueprints_usage)

    def test_blueprints_usage_using_bool(self):
        # If the old bool says they use Launchpad, return LAUNCHPAD
        # if the ServiceUsage is unknown.
        login_person(self.distribution.owner)
        self.distribution.official_blueprints = True
        self.assertEqual(
            ServiceUsage.LAUNCHPAD,
            self.distribution.blueprints_usage)

    def test_blueprints_usage_with_enum_data(self):
        # If the enum has something other than UNKNOWN as its status,
        # use that.
        login_person(self.distribution.owner)
        self.distribution.blueprints_usage = ServiceUsage.EXTERNAL
        self.assertEqual(ServiceUsage.EXTERNAL, self.distribution.blueprints_usage)


class TestDistribution(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestDistribution, self).setUp('foo.bar@canonical.com')

    def test_distribution_repr_ansii(self):
        # Verify that ANSI displayname is ascii safe.
        distro = self.factory.makeDistribution(
            name="distro", displayname=u'\xdc-distro')
        ignore, displayname, name = repr(distro).rsplit(' ', 2)
        self.assertEqual("'\\xdc-distro'", displayname)
        self.assertEqual('(distro)>', name)

    def test_distribution_repr_unicode(self):
        # Verify that Unicode displayname is ascii safe.
        distro = self.factory.makeDistribution(
            name="distro", displayname=u'\u0170-distro')
        ignore, displayname, name = repr(distro).rsplit(' ', 2)
        self.assertEqual("'\\u0170-distro'", displayname)


class TestDistributionCurrentSourceReleases(
    TestDistroSeriesCurrentSourceReleases):
    """Test for Distribution.getCurrentSourceReleases().

    This works in the same way as
    DistroSeries.getCurrentSourceReleases() works, except that we look
    for the latest published source across multiple distro series.
    """

    layer = LaunchpadFunctionalLayer
    release_interface = IDistributionSourcePackageRelease

    @property
    def test_target(self):
        return self.distribution

    def test_which_distroseries_does_not_matter(self):
        # When checking for the current release, we only care about the
        # version numbers. We don't care whether the version is
        # published in a earlier or later series.
        self.current_series = self.factory.makeDistroRelease(
            self.distribution, '1.0', status=SeriesStatus.CURRENT)
        self.publisher.getPubSource(
            version='0.9', distroseries=self.current_series)
        self.publisher.getPubSource(
            version='1.0', distroseries=self.development_series)
        self.assertCurrentVersion('1.0')

        self.publisher.getPubSource(
            version='1.1', distroseries=self.current_series)
        self.assertCurrentVersion('1.1')

    def test_distribution_series_cache(self):
        distribution = removeSecurityProxy(
            self.factory.makeDistribution('foo'))

        # Not yet cached.
        missing = object()
        cached_series = getattr(distribution, '_cached_series', missing)
        self.assertEqual(missing, cached_series)

        # Now cached.
        series = distribution.series
        self.assertTrue(series is distribution._cached_series)

        # Cache cleared.
        distribution.newSeries(
            name='bar', displayname='Bar', title='Bar', summary='',
            description='', version='1', parent_series=None,
            owner=self.factory.makePerson())
        cached_series = getattr(distribution, '_cached_series', missing)
        self.assertEqual(missing, cached_series)

        # New cached value.
        series = distribution.series
        self.assertEqual(1, len(series))
        self.assertTrue(series is distribution._cached_series)


class SeriesByStatusTests(TestCaseWithFactory):
    """Test IDistribution.getSeriesByStatus().
    """

    layer = LaunchpadFunctionalLayer

    def test_get_none(self):
        distro = self.factory.makeDistribution()
        self.assertEquals([],
            list(distro.getSeriesByStatus(SeriesStatus.FROZEN)))

    def test_get_current(self):
        distro = self.factory.makeDistribution()
        series = self.factory.makeDistroSeries(distribution=distro,
            status=SeriesStatus.CURRENT)
        self.assertEquals([series],
            list(distro.getSeriesByStatus(SeriesStatus.CURRENT)))


class SeriesTests(TestCaseWithFactory):
    """Test IDistribution.getSeries().
    """

    layer = LaunchpadFunctionalLayer

    def test_get_none(self):
        distro = self.factory.makeDistribution()
        self.assertRaises(NoSuchDistroSeries, distro.getSeries, "astronomy")

    def test_get_by_name(self):
        distro = self.factory.makeDistribution()
        series = self.factory.makeDistroSeries(distribution=distro,
            name="dappere")
        self.assertEquals(series, distro.getSeries("dappere"))

    def test_get_by_version(self):
        distro = self.factory.makeDistribution()
        series = self.factory.makeDistroSeries(distribution=distro,
            name="dappere", version="42.6")
        self.assertEquals(series, distro.getSeries("42.6"))


class DistroSnapshotTestCase(TestCaseWithFactory):
    """A TestCase for distribution snapshots."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(DistroSnapshotTestCase, self).setUp()
        self.distribution = self.factory.makeDistribution(name="boobuntu")

    def test_snapshot(self):
        """Snapshots of products should not include marked attribues.

        Wrap an export with 'doNotSnapshot' to force the snapshot to not
        include that attribute.
        """
        snapshot = Snapshot(self.distribution, providing=IDistribution)
        omitted = [
            'archive_mirrors',
            'cdimage_mirrors',
            'series',
            'all_distro_archives',
            ]
        for attribute in omitted:
            self.assertFalse(
                hasattr(snapshot, attribute),
                "Snapshot should not include %s." % attribute)
