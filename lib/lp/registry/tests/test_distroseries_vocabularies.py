# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for distroseries vocabularies in `lp.registry.vocabularies`."""

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
from lp.registry.interfaces.distroseries import IDistroSeriesSet
from lp.registry.vocabularies import DistroSeriesDerivationVocabularyFactory
from lp.testing import TestCaseWithFactory


class TestDistroSeriesDerivationVocabularyFactory(TestCaseWithFactory):
    """Tests for `DistroSeriesDerivationVocabularyFactory`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestDistroSeriesDerivationVocabularyFactory, self).setUp()
        self.vocabulary_factory = DistroSeriesDerivationVocabularyFactory()
        self.all_distroseries = getUtility(IDistroSeriesSet).search()

    def test_interface(self):
        # DistroSeriesDerivationVocabularyFactory instances provides
        # IContextSourceBinder.
        self.assertProvides(
            self.vocabulary_factory, IContextSourceBinder)

    def test_distribution_without_series(self):
        # Given a distribution without any series, the vocabulary factory
        # returns a vocabulary for all distroseries in all distributions.
        distribution = self.factory.makeDistribution()
        vocabulary = self.vocabulary_factory(distribution)
        expected_distroseries = set(self.all_distroseries)
        observed_distroseries = set(term.value for term in vocabulary)
        self.assertEqual(expected_distroseries, observed_distroseries)

    def test_distribution_with_non_derived_series(self):
        # Given a distribution with series, none of which are derived, the
        # vocabulary factory returns a vocabulary for all distroseries in all
        # distributions *except* the given distribution.
        distroseries = self.factory.makeDistroSeries()
        vocabulary = self.vocabulary_factory(distroseries.distribution)
        expected_distroseries = (
            set(self.all_distroseries) - set(distroseries.distribution))
        observed_distroseries = set(term.value for term in vocabulary)
        self.assertEqual(expected_distroseries, observed_distroseries)

    def test_distribution_with_derived_series(self):
        # Given a distribution with series, one or more of which are derived,
        # the vocabulary factory returns a vocabulary for all distroseries of
        # the distribution from which the derived series have been derived.
        parent_distroseries = self.factory.makeDistroSeries()
        distroseries = self.factory.makeDistroSeries(
            parent_series=parent_distroseries)
        vocabulary = self.vocabulary_factory(distroseries.distribution)
        expected_distroseries = set(parent_distroseries.distribution)
        observed_distroseries = set(term.value for term in vocabulary)
        self.assertEqual(expected_distroseries, observed_distroseries)

    def test_distribution_with_derived_series_of_self(self):
        # Given a distribution with series derived from other of its series
        # (which shouldn't happen), the vocabulary factory returns a
        # vocabulary for all distroseries in all distributions *except* the
        # given distribution.
        parent_distroseries = self.factory.makeDistroSeries()
        distroseries = self.factory.makeDistroSeries(
            distribution=parent_distroseries.distribution,
            parent_series=parent_distroseries)
        vocabulary = self.vocabulary_factory(distroseries.distribution)
        expected_distroseries = (
            set(self.all_distroseries) - set(distroseries.distribution))
        observed_distroseries = set(term.value for term in vocabulary)
        self.assertEqual(expected_distroseries, observed_distroseries)

    def test_distroseries(self):
        # Given a distroseries, the vocabulary factory returns the vocabulary
        # the same as for its distribution.
        distroseries = self.factory.makeDistroSeries()
        vocabulary = self.vocabulary_factory(distroseries)
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

        vocabulary = self.vocabulary_factory(ccc)
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
