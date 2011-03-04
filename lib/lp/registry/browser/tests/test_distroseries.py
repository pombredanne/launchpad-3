# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `lp.registry.browser.distroseries`."""

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )

from pytz import utc
from zope.component import getUtility
from zope.schema.interfaces import IContextSourceBinder
from zope.security.proxy import removeSecurityProxy

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

    def test_ordering(self):
        # The vocabulary is sorted by distribution display name then by the
        # date the distroseries was created, newest first.
        now = datetime.now(utc)
        two_days_ago = now - timedelta(2)
        six_days_ago = now - timedelta(7)

        aaa = self.factory.makeDistribution(displayname="aaa")
        aaa_series_older = self.factory.makeDistroSeries(
            name="aaa-series-older", distribution=aaa)
        removeSecurityProxy(aaa_series_older).date_created = six_days_ago
        aaa_series_newer = self.factory.makeDistroSeries(
            name="aaa-series-newer", distribution=aaa)
        removeSecurityProxy(aaa_series_newer).date_created = two_days_ago

        bbb = self.factory.makeDistribution(displayname="bbb")
        bbb_series_older = self.factory.makeDistroSeries(
            name="bbb-series-older", distribution=bbb)
        removeSecurityProxy(bbb_series_older).date_created = six_days_ago
        bbb_series_newer = self.factory.makeDistroSeries(
            name="bbb-series-newer", distribution=bbb)
        removeSecurityProxy(bbb_series_newer).date_created = two_days_ago

        ccc = self.factory.makeDistribution(displayname="ccc")

        vocabulary = derived_from_series_source(ccc)
        expected_distroseries = [
            aaa_series_newer, aaa_series_older,
            bbb_series_newer, bbb_series_older]
        observed_distroseries = list(term.value for term in vocabulary)
        # observed_distroseries will contain distroseries from the sample
        # data, so we must only look at the set of distroseries we have
        # created.
        observed_distroseries = [
            series for series in observed_distroseries
            if series in expected_distroseries]
        self.assertEqual(expected_distroseries, observed_distroseries)


class TestDistroSeriesInitializeView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_init(self):
        # There exists a +initseries view for distroseries.
        distroseries = self.factory.makeDistroSeries()
        view = create_initialized_view(distroseries, "+initseries")
        self.assertTrue(view)
