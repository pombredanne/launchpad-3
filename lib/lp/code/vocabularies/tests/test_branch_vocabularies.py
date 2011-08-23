# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the branch vocabularies."""

__metaclass__ = type

from unittest import TestCase

from zope.component import getUtility

from canonical.launchpad.ftests import (
    ANONYMOUS,
    login,
    logout,
    )
from lp.code.vocabularies.branch import (
    BranchRestrictedOnProductVocabulary,
    BranchVocabulary,
    )
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.code.interfaces.branchlookup import IBranchLookup
from lp.registry.interfaces.product import IProductSet
from lp.testing.factory import LaunchpadObjectFactory


class BranchVocabTestCase(TestCase):
    """A base class for the branch vocabulary test cases."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Set up the anonymous security interaction.
        login(ANONYMOUS)

    def tearDown(self):
        logout()


class TestBranchVocabulary(BranchVocabTestCase):
    """Test that the BranchVocabulary behaves as expected."""

    def setUp(self):
        BranchVocabTestCase.setUp(self)
        self._createBranches()
        self.vocab = BranchVocabulary(context=None)

    def _createBranches(self):
        factory = LaunchpadObjectFactory()
        widget = factory.makeProduct(name='widget')
        sprocket = factory.makeProduct(name='sprocket')
        # Scotty's branches.
        scotty = factory.makePerson(name='scotty')
        factory.makeProductBranch(
            owner=scotty, product=widget, name='fizzbuzz')
        factory.makeProductBranch(
            owner=scotty, product=widget, name='mountain')
        factory.makeProductBranch(
            owner=scotty, product=sprocket, name='fizzbuzz')
        # Spotty's branches.
        spotty = factory.makePerson(name='spotty')
        factory.makeProductBranch(
            owner=spotty, product=widget, name='hill')
        factory.makeProductBranch(
            owner=spotty, product=widget, name='sprocket')
        # Sprocket's branches.
        sprocket_person = factory.makePerson(name='sprocket')
        factory.makeProductBranch(
            owner=sprocket_person, product=widget, name='foo')

    def test_fizzbuzzBranches(self):
        """Return branches that match the string 'fizzbuzz'."""
        results = self.vocab.searchForTerms('fizzbuzz')
        expected = [
            u'~scotty/sprocket/fizzbuzz',
            u'~scotty/widget/fizzbuzz',
            ]
        branch_names = sorted([branch.token for branch in results])
        self.assertEqual(expected, branch_names)

    def test_widgetBranches(self):
        """Searches match the product name too."""
        results = self.vocab.searchForTerms('widget')
        expected = [
            u'~scotty/widget/fizzbuzz',
            u'~scotty/widget/mountain',
            u'~spotty/widget/hill',
            u'~spotty/widget/sprocket',
            u'~sprocket/widget/foo',
            ]
        branch_names = sorted([branch.token for branch in results])
        self.assertEqual(expected, branch_names)

    def test_spottyBranches(self):
        """Searches also match the registrant name."""
        results = self.vocab.searchForTerms('spotty')
        expected = [
            u'~spotty/widget/hill',
            u'~spotty/widget/sprocket',
            ]
        branch_names = sorted([branch.token for branch in results])
        self.assertEqual(expected, branch_names)

    def test_crossAttributeBranches(self):
        """The search checks name, product, and person."""
        results = self.vocab.searchForTerms('rocket')
        expected = [
            u'~scotty/sprocket/fizzbuzz',
            u'~spotty/widget/sprocket',
            u'~sprocket/widget/foo',
            ]
        branch_names = sorted([branch.token for branch in results])
        self.assertEqual(expected, branch_names)

    def test_singleQueryResult(self):
        # If there is a single search result that matches, use that
        # as the result.
        term = self.vocab.getTermByToken('mountain')
        self.assertEqual(
            '~scotty/widget/mountain',
            term.value.unique_name)

    def test_multipleQueryResult(self):
        # If there are more than one search result, a LookupError is still
        # raised.
        self.assertRaises(
            LookupError,
            self.vocab.getTermByToken,
            'fizzbuzz')


class TestRestrictedBranchVocabularyOnProduct(BranchVocabTestCase):
    """Test the BranchRestrictedOnProductVocabulary behaves as expected.

    When a BranchRestrictedOnProductVocabulary is used with a product the
    product of the branches in the vocabulary match the product given as the
    context.
    """

    def setUp(self):
        BranchVocabTestCase.setUp(self)
        self._createBranches()
        self.vocab = BranchRestrictedOnProductVocabulary(
            context=self._getVocabRestriction())

    def _getVocabRestriction(self):
        """Restrict using the widget product."""
        return getUtility(IProductSet).getByName('widget')

    def _createBranches(self):
        factory = LaunchpadObjectFactory()
        test_product = factory.makeProduct(name='widget')
        other_product = factory.makeProduct(name='sprocket')
        person = factory.makePerson(name='scotty')
        factory.makeProductBranch(
            owner=person, product=test_product, name='main')
        factory.makeProductBranch(
            owner=person, product=test_product, name='mountain')
        factory.makeProductBranch(
            owner=person, product=other_product, name='main')
        person = factory.makePerson(name='spotty')
        factory.makeProductBranch(
            owner=person, product=test_product, name='hill')

    def test_mainBranches(self):
        """Look for widget's main branch.

        The result set should not show ~scotty/sprocket/main.
        """
        results = self.vocab.searchForTerms('main')
        expected = [
            u'~scotty/widget/main',
            ]
        branch_names = sorted([branch.token for branch in results])
        self.assertEqual(expected, branch_names)

    def test_ownersBranches(self):
        """Look for branches owned by scotty.

        The result set should not show ~scotty/sprocket/main.
        """
        results = self.vocab.searchForTerms('scotty')

        expected = [
            u'~scotty/widget/main',
            u'~scotty/widget/mountain',
            ]
        branch_names = sorted([branch.token for branch in results])
        self.assertEqual(expected, branch_names)

    def test_singleQueryResult(self):
        # If there is a single search result that matches, use that
        # as the result.
        term = self.vocab.getTermByToken('mountain')
        self.assertEqual(
            '~scotty/widget/mountain',
            term.value.unique_name)

    def test_multipleQueryResult(self):
        # If there are more than one search result, a LookupError is still
        # raised.
        self.assertRaises(
            LookupError,
            self.vocab.getTermByToken,
            'scotty')


class TestRestrictedBranchVocabularyOnBranch(
    TestRestrictedBranchVocabularyOnProduct):
    """Test the BranchRestrictedOnProductVocabulary behaves as expected.

    When a BranchRestrictedOnProductVocabulary is used with a branch the
    product of the branches in the vocabulary match the product of the branch
    that is the context.
    """

    def _getVocabRestriction(self):
        """Restrict using a branch on widget."""
        return getUtility(IBranchLookup).getByUniqueName(
            '~spotty/widget/hill')
