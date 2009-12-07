# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the milestone vocabularies."""

__metaclass__ = type

from unittest import TestLoader
from operator import attrgetter

from lp.registry.vocabularies import ProductSeriesVocabulary
from lp.testing import TestCaseWithFactory

from canonical.testing import DatabaseFunctionalLayer


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

    def tearDown(self):
        super(TestProductSeriesVocabulary, self).tearDown()

    def test_search(self):
        series2 = self.factory.makeProductSeries(product=self.product)
        # Search by product name.
        result = self.vocabulary.search(self.product.name)
        self.assertEqual(
            [self.series, series2].sort(key=attrgetter('id')),
            list(result).sort(key=attrgetter('id')))
        # Search by series name.
        result = self.vocabulary.search(self.series.name)
        self.assertEqual([self.series], list(result))
        # Search by series2 name.
        result = self.vocabulary.search(series2.name)
        self.assertEqual([series2], list(result))
        # Search by product & series name substrings.
        result = self.vocabulary.search(
            '%s/%s' % (self.product_prefix, self.series1_prefix))
        self.assertEqual([self.series], list(result))

    def test_toTerm(self):
        term = self.vocabulary.toTerm(self.series)
        self.assertEqual(
            '%s/%s' % (self.product.name, self.series.name),
            term.token)
        self.assertEqual(self.series, term.value)

    def test_getTermByToken(self):
        token = '%s/%s' % (self.product.name, self.series.name)
        term = self.vocabulary.getTermByToken(token)
        self.assertEqual(token, term.token)
        self.assertEqual(self.series, term.value)

    def test_getTermByToken_LookupError(self):
        self.assertRaises(
            LookupError,
            self.vocabulary.getTermByToken, 'does/notexist')


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
