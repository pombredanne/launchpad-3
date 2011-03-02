# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `lp.registry.browser.distroseries`."""

__metaclass__ = type

from zope.component import getUtility
from zope.schema.interfaces import IContextSourceBinder

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.browser.distroseries import derived_from_series_source
from lp.testing import TestCaseWithFactory
from lp.testing.views import create_initialized_view


class TestDerivedFromSeriesSource(TestCaseWithFactory):
    """Tests for the `derived_from_series_source` vocabulary factory."""

    layer = DatabaseFunctionalLayer

    def test_interface(self):
        # derived_from_series_source provides IContextSourceBinder.
        self.assertProvides(
            derived_from_series_source, IContextSourceBinder)

    def test_distroseries(self):
        # Given a distroseries, derived_from_series_source returns a
        # vocabulary for its distribution's serieses.
        distro_series = self.factory.makeDistroSeries()
        vocabulary = derived_from_series_source(distro_series)
        self.assertEqual(
            [series for series in distro_series.distribution],
            [term.value for term in vocabulary])

    def test_distribution(self):
        # Given a distribution, derived_from_series_source returns a
        # vocabulary for its serieses.
        distro_series = self.factory.makeDistroSeries()
        vocabulary = derived_from_series_source(distro_series.distribution)
        self.assertEqual(
            [series for series in distro_series.distribution],
            [term.value for term in vocabulary])

    def test_distribution_without_series(self):
        # Given a distribution without any series, derived_from_series_source
        # returns a vocabulary for *Ubuntu's* serieses.
        distribution = self.factory.makeDistribution()
        vocabulary = derived_from_series_source(distribution)
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self.assertEqual(
            [series for series in ubuntu],
            [term.value for term in vocabulary])


class TestDistroSeriesInitializeView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_init(self):
        # There exists a +initseries view for distroseries.
        distro_series = self.factory.makeDistroSeries()
        view = create_initialized_view(distro_series, "+initseries")
        self.assertTrue(view)
