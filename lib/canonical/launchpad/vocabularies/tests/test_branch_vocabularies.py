# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test the branch vocabularies."""

__metaclass__ = type
__all__ = []

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
        query = self.vocab._search('')
        self.assertEqual('', query, "Expected empty query and got %r" % query)

    def test_correctCount(self):
        results = self.vocab.search('')
        self.assertEqual(30, results.count())

    def test_mainBranches(self):
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
        results = self.vocab.search('vcs-imports')
        expected = [
            u'~vcs-imports/evolution/import',
            u'~vcs-imports/evolution/main',
            u'~vcs-imports/gnome-terminal/import']
        branch_names = sorted([branch.unique_name for branch in results])
        self.assertEqual(expected, branch_names)

    def test_branchesThatHaveB(self):
        results = self.vocab.search('b')

        built_strings = ['%s %s' % (branch.unique_name, branch.url)
                         for branch in results]

        for mash_up in built_strings:
            self.assertTrue('b' in mash_up, "%r doesn't have a b" % mash_up)


class TestRestrictedBranchVocabularyOnProduct(BranchVocabTestCase):
    """Test the BranchRestrictedOnProductVocabulary behaves as expected."""

    def setUp(self):
        BranchVocabTestCase.setUp(self)
        self.product = getUtility(IProductSet).getByName('gnome-terminal')
        self.vocab = BranchRestrictedOnProductVocabulary(context=self.product)

    def test_correctCount(self):
        results = self.vocab.search('')
        self.assertEqual(10, results.count())

    def test_mainBranches(self):
        results = self.vocab.search('main')
        expected = [
            u'~name12/gnome-terminal/main',
            ]
        branch_names = sorted([branch.unique_name for branch in results])
        self.assertEqual(expected, branch_names)

    def test_orBranches(self):
        results = self.vocab.search('or')

        built_strings = ['%s %s' % (branch.unique_name, branch.url)
                         for branch in results]

        for mash_up in built_strings:
            self.assertTrue('or' in mash_up, "%r doesn't have 'or'" % mash_up)


class TestRestrictedBranchVocabularyOnBranch(BranchVocabTestCase):
    """Test the BranchRestrictedOnProductVocabulary behaves as expected."""

    def setUp(self):
        BranchVocabTestCase.setUp(self)
        self.branch = getUtility(IBranchSet).getByUniqueName(
            '~name12/gnome-terminal/main')
        self.vocab = BranchRestrictedOnProductVocabulary(context=self.branch)

    def test_correctCount(self):
        # Make sure that branch count is correct given that two gnome-terminal
        # branches are private.
        results = self.vocab.search('')
        self.assertEqual(10, results.count())

    def test_mainBranches(self):
        results = self.vocab.search('main')
        expected = [
            u'~name12/gnome-terminal/main',
            ]
        branch_names = sorted([branch.unique_name for branch in results])
        self.assertEqual(expected, branch_names)

    def test_orBranches(self):
        results = self.vocab.search('or')

        built_strings = ['%s %s' % (branch.unique_name, branch.url)
                         for branch in results]

        for mash_up in built_strings:
            self.assertTrue('or' in mash_up, "%r doesn't have 'or'" % mash_up)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
