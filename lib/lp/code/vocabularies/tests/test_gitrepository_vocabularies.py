# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the Git repository vocabularies."""

__metaclass__ = type

from lp.code.interfaces.gitrepository import GIT_FEATURE_FLAG
from lp.code.vocabularies.gitrepository import GitRepositoryVocabulary
from lp.services.features.testing import FeatureFixture
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class TestGitRepositoryVocabulary(TestCaseWithFactory):
    """Test that the GitRepositoryVocabulary behaves as expected."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestGitRepositoryVocabulary, self).setUp()
        self.useFixture(FeatureFixture({GIT_FEATURE_FLAG: u"on"}))
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
