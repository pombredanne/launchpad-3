# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Distribution."""

__metaclass__ = type

from lazr.lifecycle.snapshot import Snapshot
import soupmatchers
from testtools.matchers import (
    MatchesAny,
    Not,
    )
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp import canonical_url
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.registry.errors import NoSuchDistroSeries
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.series import SeriesStatus
from lp.registry.tests.test_distroseries import (
    TestDistroSeriesCurrentSourceReleases,
    )
from lp.services.propertycache import get_property_cache
from lp.soyuz.interfaces.distributionsourcepackagerelease import (
    IDistributionSourcePackageRelease,
    )
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


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

        cache = get_property_cache(distribution)

        # Not yet cached.
        self.assertNotIn("series", cache)

        # Now cached.
        series = distribution.series
        self.assertIs(series, cache.series)

        # Cache cleared.
        distribution.newSeries(
            name='bar', displayname='Bar', title='Bar', summary='',
            description='', version='1', parent_series=None,
            owner=self.factory.makePerson())
        self.assertNotIn("series", cache)

        # New cached value.
        series = distribution.series
        self.assertEqual(1, len(series))
        self.assertIs(series, cache.series)


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


class TestDistributionPage(TestCaseWithFactory):
    """A TestCase for the distribution page."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestDistributionPage, self).setUp('foo.bar@canonical.com')
        self.distro = self.factory.makeDistribution(
            name="distro", displayname=u'distro')
        self.admin = getUtility(IPersonSet).getByEmail(
            'admin@canonical.com')
        self.simple_user = self.factory.makePerson()

    def test_distributionpage_addseries_link(self):
        """ Verify that an admin sees the +addseries link."""
        login_person(self.admin)
        view = create_initialized_view(
            self.distro, '+index', principal=self.admin)
        series_matches = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                'link to add a series', 'a',
                attrs={'href':
                    canonical_url(self.distro, view_name='+addseries')},
                text='Add series'),
            soupmatchers.Tag(
                'Series and milestones widget', 'h2',
                text='Series and milestones'),
            )
        self.assertThat(view.render(), series_matches)

    def test_distributionpage_addseries_link_noadmin(self):
        """Verify that a non-admin does not see the +addseries link
        nor the series header (since there is no series yet).
        """
        login_person(self.simple_user)
        view = create_initialized_view(
            self.distro, '+index', principal=self.simple_user)
        add_series_match = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                'link to add a series', 'a',
                attrs={'href':
                    canonical_url(self.distro, view_name='+addseries')},
                text='Add series'))
        series_header_match = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                'Series and milestones widget', 'h2',
                text='Series and milestones'))
        self.assertThat(
            view.render(),
            Not(MatchesAny(add_series_match, series_header_match)))

    def test_distributionpage_series_list_noadmin(self):
        """Verify that a non-admin does see the series list
        when there is a series.
        """
        series = self.factory.makeDistroSeries(distribution=self.distro,
            status=SeriesStatus.CURRENT)
        login_person(self.simple_user)
        view = create_initialized_view(
            self.distro, '+index', principal=self.simple_user)
        add_series_match = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                'link to add a series', 'a',
                attrs={'href':
                    canonical_url(self.distro, view_name='+addseries')},
                text='Add series'))
        series_header_match = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                'Series and milestones widget', 'h2',
                text='Series and milestones'))
        self.assertThat(view.render(), series_header_match)
        self.assertThat(view.render(), Not(add_series_match))


class DistroRegistrantTestCase(TestCaseWithFactory):
    """A TestCase for registrants and owners of a distribution.

    The registrant is the creator of the distribution (read-only field).
    The owner is really the maintainer.
    """

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(DistroRegistrantTestCase, self).setUp()
        self.owner = self.factory.makePerson()
        self.registrant = self.factory.makePerson()

    def test_distro_registrant_owner_differ(self):
        distribution = self.factory.makeDistribution(
            name="boobuntu", owner=self.owner, registrant=self.registrant)
        self.assertNotEqual(distribution.owner, distribution.registrant)
        self.assertEqual(distribution.owner, self.owner)
        self.assertEqual(distribution.registrant, self.registrant)
