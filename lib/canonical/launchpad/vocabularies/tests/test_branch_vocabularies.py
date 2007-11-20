# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test the branch vocabularies."""

__metaclass__ = type

from unittest import TestCase, TestLoader

from zope.component import getUtility

from canonical.launchpad.ftests.harness import login, logout, ANONYMOUS
from canonical.launchpad.interfaces import IBranchSet, IProductSet
from canonical.launchpad.vocabularies.dbobjects import (
    BranchRestrictedOnProductVocabulary, BranchVocabulary)
from canonical.testing import LaunchpadFunctionalLayer


class BranchVocabTestCase(TestCase):
    """A base class for the branch vocabulary test cases."""
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login(ANONYMOUS)

    def tearDown(self):
        logout()


class TestBranchVocabulary(BranchVocabTestCase):
    """Test that the BranchVocabulary behavies as expected."""

    def setUp(self):
        BranchVocabTestCase.setUp(self)
        self.vocab = BranchVocabulary(context=None)

    def test_emptySearch(self):
        """An empty search should return an empty query."""
        query = self.vocab._search('')
        self.assertEqual('', query, "Expected empty query and got %r" % query)

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
        results = self.vocab.search('vcs-imports')
        expected = [
            u'~vcs-imports/evolution/import',
            u'~vcs-imports/evolution/main',
            u'~vcs-imports/gnome-terminal/import']
        branch_names = sorted([branch.unique_name for branch in results])
        self.assertEqual(expected, branch_names)

    def test_branchesThatHaveB(self):
        """Searches match the branch unique name or the url."""
        results = self.vocab.search('b')

        built_strings = ['%s %s' % (branch.unique_name, branch.url)
                         for branch in results]

        self.assertTrue(
            len(built_strings) > 0, 'There are not any branches that match.')
        for mash_up in built_strings:
            self.assertTrue('b' in mash_up, "%r doesn't have a b" % mash_up)


class TestRestrictedBranchVocabularyOnProduct(BranchVocabTestCase):
    """Test the BranchRestrictedOnProductVocabulary behaves as expected.

    When a BranchRestrictedOnProductVocabulary is used with a product the
    product of the branches in the vocabulary match the product given as the
    context.
    """

    def setUp(self):
        BranchVocabTestCase.setUp(self)
        self.product = getUtility(IProductSet).getByName('gnome-terminal')
        self.vocab = BranchRestrictedOnProductVocabulary(context=self.product)

    def test_mainBranches(self):
        """Check the main branches for gnome-terminal."""
        results = self.vocab.search('main')
        expected = [
            u'~name12/gnome-terminal/main',
            ]
        branch_names = sorted([branch.unique_name for branch in results])
        self.assertEqual(expected, branch_names)

    def test_orBranches(self):
        """Look for branches for gnome-terminal that have the string 'or'."""
        results = self.vocab.search('or')

        built_strings = ['%s %s' % (branch.unique_name, branch.url)
                         for branch in results]
        self.assertTrue(
            len(built_strings) > 0, 'There are not any branches that match.')
        for mash_up in built_strings:
            self.assertTrue('or' in mash_up, "%r doesn't have 'or'" % mash_up)


class TestRestrictedBranchVocabularyOnBranch(BranchVocabTestCase):
    """Test the BranchRestrictedOnProductVocabulary behaves as expected.

    When a BranchRestrictedOnProductVocabulary is used with a branch the
    product of the branches in the vocabulary match the product of the branch
    that is the context.
    """

    def setUp(self):
        BranchVocabTestCase.setUp(self)
        self.branch = getUtility(IBranchSet).getByUniqueName(
            '~name12/gnome-terminal/main')
        self.vocab = BranchRestrictedOnProductVocabulary(context=self.branch)

    def test_mainBranches(self):
        """Check the main branches for gnome-terminal."""
        results = self.vocab.search('main')
        expected = [
            u'~name12/gnome-terminal/main',
            ]
        branch_names = sorted([branch.unique_name for branch in results])
        self.assertEqual(expected, branch_names)

    def test_orBranches(self):
        """Look for branches for gnome-terminal that have the string 'or'."""
        results = self.vocab.search('or')

        built_strings = ['%s %s' % (branch.unique_name, branch.url)
                         for branch in results]

        self.assertTrue(
            len(built_strings) > 0, 'There are not any branches that match.')
        for mash_up in built_strings:
            self.assertTrue('or' in mash_up, "%r doesn't have 'or'" % mash_up)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
