# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test the branch vocabularies."""

__metaclass__ = type

from unittest import TestCase, TestLoader

from zope.component import getUtility

from canonical.launchpad.ftests.harness import login, logout, ANONYMOUS
from canonical.launchpad.interfaces import IBranchSet, IProductSet
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.launchpad.vocabularies.dbobjects import (
    BranchRestrictedOnProductVocabulary, BranchVocabulary)
from canonical.testing import LaunchpadFunctionalLayer


class BranchVocabTestCase(TestCase):
    """A base class for the branch vocabulary test cases."""
    layer = LaunchpadFunctionalLayer

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
        factory.makeBranch(
            owner=scotty, product=widget, name='fizzbuzz')
        factory.makeBranch(
            owner=scotty, product=widget, name='mountain')
        factory.makeBranch(
            owner=scotty, product=sprocket, name='fizzbuzz')
        # Spotty's branches.
        spotty = factory.makePerson(name='spotty')
        factory.makeBranch(
            owner=spotty, product=widget, name='hill')
        factory.makeBranch(
            owner=spotty, product=widget, name='sprocket')
        # Sprocket's branches.
        sprocket_person = factory.makePerson(name='sprocket')
        factory.makeBranch(
            owner=sprocket_person, product=widget, name='foo')

    def test_emptySearch(self):
        """An empty search should return an empty query string."""
        query = self.vocab._constructNaiveQueryString('')
        self.assertEqual(
            '', query, "Expected empty query string and got %r" % query)

    def test_fizzbuzzBranches(self):
        """Return branches that match the string 'fizzbuzz'."""
        results = self.vocab.search('fizzbuzz')
        expected = [
            u'~scotty/sprocket/fizzbuzz',
            u'~scotty/widget/fizzbuzz',
            ]
        branch_names = sorted([branch.unique_name for branch in results])
        self.assertEqual(expected, branch_names)

    def test_widgetBranches(self):
        """Searches match the product name too."""
        results = self.vocab.search('widget')
        expected = [
            u'~scotty/widget/fizzbuzz',
            u'~scotty/widget/mountain',
            u'~spotty/widget/hill',
            u'~spotty/widget/sprocket',
            u'~sprocket/widget/foo',
            ]
        branch_names = sorted([branch.unique_name for branch in results])
        self.assertEqual(expected, branch_names)

    def test_spottyBranches(self):
        """Searches also match the registrant name."""
        results = self.vocab.search('spotty')
        expected = [
            u'~spotty/widget/hill',
            u'~spotty/widget/sprocket',
            ]
        branch_names = sorted([branch.unique_name for branch in results])
        self.assertEqual(expected, branch_names)

    def test_crossAttributeBranches(self):
        """The search checks name, product, and person."""
        results = self.vocab.search('rocket')
        expected = [
            u'~scotty/sprocket/fizzbuzz',
            u'~spotty/widget/sprocket',
            u'~sprocket/widget/foo',
            ]
        branch_names = sorted([branch.unique_name for branch in results])
        self.assertEqual(expected, branch_names)


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
        factory.makeBranch(
            owner=person, product=test_product, name='main')
        factory.makeBranch(
            owner=person, product=test_product, name='mountain')
        factory.makeBranch(
            owner=person, product=other_product, name='main')
        person = factory.makePerson(name='spotty')
        factory.makeBranch(
            owner=person, product=test_product, name='hill')

    def test_mainBranches(self):
        """Look for widget's main branch.

        The result set should not show ~scotty/sprocket/main.
        """
        results = self.vocab.search('main')
        expected = [
            u'~scotty/widget/main',
            ]
        branch_names = sorted([branch.unique_name for branch in results])
        self.assertEqual(expected, branch_names)

    def test_ownersBranches(self):
        """Look for branches owned by scotty.

        The result set should not show ~scotty/sprocket/main.
        """
        results = self.vocab.search('scotty')

        expected = [
            u'~scotty/widget/main',
            u'~scotty/widget/mountain',
            ]
        branch_names = sorted([branch.unique_name for branch in results])
        self.assertEqual(expected, branch_names)


class TestRestrictedBranchVocabularyOnBranch(
    TestRestrictedBranchVocabularyOnProduct):
    """Test the BranchRestrictedOnProductVocabulary behaves as expected.

    When a BranchRestrictedOnProductVocabulary is used with a branch the
    product of the branches in the vocabulary match the product of the branch
    that is the context.
    """

    def _getVocabRestriction(self):
        """Restrict using a branch on widget."""
        return getUtility(IBranchSet).getByUniqueName('~spotty/widget/hill')


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
