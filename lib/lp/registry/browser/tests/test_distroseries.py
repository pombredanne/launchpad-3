# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `lp.registry.browser.distroseries`."""

__metaclass__ = type

from zope.component import getUtility
from zope.schema.interfaces import IContextSourceBinder

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.browser.distroseries import derived_from_series_source
from lp.registry.interfaces.distroseries import IDistroSeriesSet
from lp.testing import TestCaseWithFactory
from lp.testing.views import create_initialized_view


class TestDerivedFromSeriesSource(TestCaseWithFactory):
    """Tests for the `derived_from_series_source` vocabulary factory."""

    layer = DatabaseFunctionalLayer

    @property
    def all_distroseries(self):
        return getUtility(IDistroSeriesSet).search()

    def test_interface(self):
        # derived_from_series_source provides IContextSourceBinder.
        self.assertProvides(
            derived_from_series_source, IContextSourceBinder)

    def test_distribution_without_series(self):
        # Given a distribution without any series, derived_from_series_source
        # returns a vocabulary for all distroseries in all distributions.
        distribution = self.factory.makeDistribution()
        vocabulary = derived_from_series_source(distribution)
        expected_distroseries = set(self.all_distroseries)
        observed_distroseries = set(term.value for term in vocabulary)
        self.assertEqual(expected_distroseries, observed_distroseries)

    def test_distribution_with_non_derived_series(self):
        # Given a distribution with series, none of which are derived,
        # derived_from_series_source returns a vocabulary for all distroseries
        # in all distributions *except* the given distribution.
        distroseries = self.factory.makeDistroSeries()
        vocabulary = derived_from_series_source(distroseries.distribution)
        expected_distroseries = (
            set(self.all_distroseries) - set(distroseries.distribution))
        observed_distroseries = set(term.value for term in vocabulary)
        self.assertEqual(expected_distroseries, observed_distroseries)

    def test_distribution_with_derived_series(self):
        # Given a distribution with series, one or more of which are derived,
        # derived_from_series_source returns a vocabulary for all distroseries
        # of the distribution from which the derived series have been derived.
        parent_distroseries = self.factory.makeDistroSeries()
        distroseries = self.factory.makeDistroSeries(
            parent_series=parent_distroseries)
        vocabulary = derived_from_series_source(distroseries.distribution)
        expected_distroseries = set(parent_distroseries.distribution)
        observed_distroseries = set(term.value for term in vocabulary)
        self.assertEqual(expected_distroseries, observed_distroseries)

    def test_distroseries(self):
        # Given a distroseries, derived_from_series_source returns the
        # vocabulary the same as for its distribution.
        distroseries = self.factory.makeDistroSeries()
        vocabulary = derived_from_series_source(distroseries)
        expected_distroseries = (
            set(self.all_distroseries) - set(distroseries.distribution))
        observed_distroseries = set(term.value for term in vocabulary)
        self.assertEqual(expected_distroseries, observed_distroseries)


class TestDistroSeriesInitializeView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_init(self):
        # There exists a +initseries view for distroseries.
        distroseries = self.factory.makeDistroSeries()
        view = create_initialized_view(distroseries, "+initseries")
        self.assertTrue(view)
