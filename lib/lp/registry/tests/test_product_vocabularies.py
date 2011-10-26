# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the product vocabularies."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.vocabularies import ProductVocabulary
from lp.testing import (
    celebrity_logged_in,
    TestCaseWithFactory,
    )


class TestProductVocabulary(TestCaseWithFactory):
    """Test that the ProductVocabulary behaves as expected."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProductVocabulary, self).setUp()
        self.vocabulary = ProductVocabulary()
        self.product = self.factory.makeProduct(
            name='bedbugs', displayname='BedBugs')

    def test_toTerm(self):
        # Product terms are composed of title, name, and the object.
        term = self.vocabulary.toTerm(self.product)
        self.assertEqual(self.product.title, term.title)
        self.assertEqual(self.product.name, term.token)
        self.assertEqual(self.product, term.value)

    def test_getTermByToken(self):
        # Tokens are case insentive because the product name is lowercase.
        term = self.vocabulary.getTermByToken('BedBUGs')
        self.assertEqual(self.product, term.value)

    def test_getTermByToken_LookupError(self):
        # getTermByToken() raises a LookupError when no match is found.
        self.assertRaises(
            LookupError,
            self.vocabulary.getTermByToken, 'does-notexist')

    def test_search_in_any_case(self):
        # Search is case insensitive and uses stem rules.
        result = self.vocabulary.search('BEDBUG')
        self.assertEqual([self.product], list(result))

    def test_order_by_displayname(self):
        # Results are ordered by displayname.
        z_product = self.factory.makeProduct(
            name='mule', displayname='Bed zebra')
        a_product = self.factory.makeProduct(
            name='orange', displayname='Bed apple')
        result = self.vocabulary.search('bed')
        self.assertEqual(
            [a_product, z_product, self.product], list(result))

    def test_order_by_relevance(self):
        # When the flag is enabled, the most relevant result is first.
        bar_product = self.factory.makeProduct(
            name='foo-bar', displayname='Foo bar', summary='quux')
        quux_product = self.factory.makeProduct(
            name='foo-quux', displayname='Foo quux')
        result = self.vocabulary.search('quux')
        self.assertEqual(
            [quux_product, bar_product], list(result))

    def test_exact_match_is_first(self):
        # When the flag is enabled, an exact name match always wins.
        the_quux_product = self.factory.makeProduct(
            name='the-quux', displayname='The quux')
        quux_product = self.factory.makeProduct(
            name='quux', displayname='The quux')
        result = self.vocabulary.search('quux')
        self.assertEqual(
            [quux_product, the_quux_product], list(result))

    def test_inactive_products_are_excluded(self):
        # Inactive products are not in the vocabulary.
        with celebrity_logged_in('registry_experts'):
            self.product.active = False
        result = self.vocabulary.search('bedbugs')
        self.assertEqual([], list(result))
