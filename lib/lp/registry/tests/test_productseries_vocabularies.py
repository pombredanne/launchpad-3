# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the milestone vocabularies."""

__metaclass__ = type

from operator import attrgetter

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.vocabularies import ProductSeriesVocabulary
from lp.testing import TestCaseWithFactory


class TestProductSeriesVocabulary(TestCaseWithFactory):
    """Test that the ProductSeriesVocabulary behaves as expected."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProductSeriesVocabulary, self).setUp()
        self.vocabulary = ProductSeriesVocabulary()
        self.product_prefix = 'asdf987-'
        self.series1_prefix = 'qwerty-'
        self.product = self.factory.makeProduct(
            self.product_prefix + 'product1')
        self.series = self.factory.makeProductSeries(
            product=self.product, name=self.series1_prefix + "series1")
        self.series2 = self.factory.makeProductSeries(product=self.product)

    def tearDown(self):
        super(TestProductSeriesVocabulary, self).tearDown()

    def test_search_by_product_name(self):
        # Test that searching by the product name finds all its series.
        result = self.vocabulary.search(self.product.name)
        self.assertEqual(
            [self.series, self.series2].sort(key=attrgetter('id')),
            list(result).sort(key=attrgetter('id')))

    def test_search_by_series_name(self):
        # Test that searching by the series name finds the right one.
        result = self.vocabulary.search(self.series.name)
        self.assertEqual([self.series], list(result))
        result = self.vocabulary.search(self.series2.name)
        self.assertEqual([self.series2], list(result))

    def test_search_by_product_and_series_name(self):
        # Test that a search string containing a slash will perform
        # a substring match on the product name with the term before
        # the slash and a substring match on the series name with
        # the term after the slash.
        result = self.vocabulary.search(
            '%s/%s' % (self.product_prefix, self.series1_prefix))
        self.assertEqual([self.series], list(result))

    def test_toTerm(self):
        # Test the ProductSeriesVocabulary.toTerm() method.
        term = self.vocabulary.toTerm(self.series)
        self.assertEqual(
            '%s/%s' % (self.product.name, self.series.name),
            term.token)
        self.assertEqual(self.series, term.value)

    def test_getTermByToken(self):
        # Test the ProductSeriesVocabulary.getTermByToken() method.
        token = '%s/%s' % (self.product.name, self.series.name)
        term = self.vocabulary.getTermByToken(token)
        self.assertEqual(token, term.token)
        self.assertEqual(self.series, term.value)

    def test_getTermByToken_LookupError(self):
        # Test that ProductSeriesVocabulary.getTermByToken() raises
        # the correct exception type when no match is found.
        self.assertRaises(
            LookupError,
            self.vocabulary.getTermByToken, 'does/notexist')
