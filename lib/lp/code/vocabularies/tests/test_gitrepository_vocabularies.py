# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the Git repository vocabularies."""

__metaclass__ = type

from zope.component import getUtility

from lp.code.vocabularies.gitrepository import (
    GitRepositoryRestrictedOnProductVocabulary,
    GitRepositoryVocabulary,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.product import IProductSet


class TestGitRepositoryVocabulary(TestCaseWithFactory):
    """Test that the GitRepositoryVocabulary behaves as expected."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestGitRepositoryVocabulary, self).setUp()
        self._createRepositories()
        self.vocab = GitRepositoryVocabulary(context=None)

    def _createRepositories(self):
        widget = self.factory.makeProduct(name="widget")
        sprocket = self.factory.makeProduct(name="sprocket")
        scotty = self.factory.makePerson(name="scotty")
        self.factory.makeGitRepository(
            owner=scotty, target=widget, name=u"fizzbuzz")
        self.factory.makeGitRepository(
            owner=scotty, target=widget, name=u"mountain")
        self.factory.makeGitRepository(
            owner=scotty, target=sprocket, name=u"fizzbuzz")

    def test_fizzbuzzRepositories(self):
        """Return repositories that match the string 'fizzbuzz'."""
        results = self.vocab.searchForTerms("fizzbuzz")
        expected = [
            u"~scotty/sprocket/+git/fizzbuzz", u"~scotty/widget/+git/fizzbuzz"]
        repository_names = sorted([repository.token for repository in results])
        self.assertEqual(expected, repository_names)

    def test_singleQueryResult(self):
        # If there is a single search result that matches, use that
        # as the result.
        term = self.vocab.getTermByToken("mountain")
        self.assertEqual(
            "~scotty/widget/+git/mountain", term.value.unique_name)

    def test_multipleQueryResult(self):
        # If there are more than one search result, a LookupError is still
        # raised.
        self.assertRaises(LookupError, self.vocab.getTermByToken, "fizzbuzz")


class TestRestrictedGitRepositoryVocabularyOnProduct(TestCaseWithFactory):
    """Test the GitRepositoryRestrictedOnProductVocabulary behaves as expected.

    When a GitRepositoryRestrictedOnProductVocabulary is used with a project,
    the project of the git repository in the vocabulary match the product give
    as the context.
    """

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestRestrictedGitRepositoryVocabularyOnProduct, self).setUp()
        self._createRepositories()
        self.vocab = GitRepositoryRestrictedOnProductVocabulary(
            context=self._getVocabRestriction())

    def _getVocabRestriction(self):
        """Restrict using the widget product."""
        return getUtility(IProductSet).getByName('widget')

    def _createRepositories(self):
        test_product = self.factory.makeProduct(name='widget')
        other_product = self.factory.makeProduct(name='sprocket')
        person = self.factory.makePerson(name=u'scotty')
        self.factory.makeGitRepository(
            owner=person, target=test_product, name=u'mountain')
        self.factory.makeGitRepository(
            owner=person, target=other_product, name=u'mountain')
        self.product = test_product
        self.other_product = test_product

    def test_product_restriction(self):
        """Look for widget's target default repository.

        The result set should not show ~scotty/sprocket/mountain.
        """
        results = self.vocab.searchForTerms('mountain')
        expected = [u'~scotty/widget/+git/mountain']
        repo_names = sorted([repo.token for repo in results])
        self.assertEqual(expected, repo_names)

    def test_singleQueryResult(self):
        # If there is a single search result that matches, use that
        # as the result.
        term = self.vocab.getTermByToken('mountain')
        self.assertEqual(
            u'~scotty/widget/+git/mountain', term.value.unique_name)

    def test_multipleQueryResult(self):
        # If there are more than one search result, a LookupError is still
        # raised.
        self.assertRaises(LookupError, self.vocab.getTermByToken, 'scotty')
