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
        self.vocab = BranchVocabulary(context=None)

    def test_emptySearch(self):
        """An empty search should return an empty query string."""
        query = self.vocab._constructNaiveQueryString('')
        self.assertEqual(
            '', query, "Expected empty query string and got %r" % query)

    def test_mainBranches(self):
        """Return branches that match the string 'main'."""
        results = self.vocab.search('main')
        expected = [
            u'~justdave/+junk/main',
            u'~kiko/+junk/main',
            u'~name12/firefox/main',
            u'~name12/gnome-terminal/main',
            u'~stevea/thunderbird/main',
            u'~vcs-imports/evolution/main']
        branch_names = sorted([branch.unique_name for branch in results])
        self.assertEqual(expected, branch_names)

    def test_firefoxBranches(self):
        """Searches match the product name too."""
        results = self.vocab.search('firefox')
        expected = [
            u'~name12/firefox/main',
            u'~sabdfl/firefox/release--0.9.1',
            u'~sabdfl/firefox/release-0.8',
            u'~sabdfl/firefox/release-0.9',
            u'~sabdfl/firefox/release-0.9.2']
        branch_names = sorted([branch.unique_name for branch in results])
        self.assertEqual(expected, branch_names)

    def test_vcsImportsBranches(self):
        """Searches also match the registrant name."""
        results = self.vocab.search('spiv')
        expected = [
            u'~spiv/+junk/feature',
            u'~spiv/+junk/feature2',
            u'~spiv/+junk/trunk']
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
