# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Vocabularies that contain Git repositories."""

__metaclass__ = type

__all__ = [
    'GitRepositoryRestrictedOnProductVocabulary',
    'GitRepositoryVocabulary',
    ]

from zope.component import getUtility
from zope.interface import implementer
from zope.schema.vocabulary import SimpleTerm

from lp.code.interfaces.gitcollection import IAllGitRepositories
from lp.code.model.gitrepository import GitRepository
from lp.registry.interfaces.product import IProduct
from lp.services.webapp.interfaces import ILaunchBag
from lp.services.webapp.vocabulary import (
    CountableIterator,
    IHugeVocabulary,
    StormVocabularyBase,
    )


@implementer(IHugeVocabulary)
class GitRepositoryVocabulary(StormVocabularyBase):
    """A vocabulary for searching Git repositories."""

    _table = GitRepository
    _order_by = ['name', 'id']
    displayname = 'Select a Git repository'
    step_title = 'Search'

    def toTerm(self, repository):
        """The display should include the URL if there is one."""
        return SimpleTerm(
            repository, repository.unique_name, repository.unique_name)

    def getTermByToken(self, token):
        """See `IVocabularyTokenized`."""
        search_results = self.searchForTerms(token)
        if search_results.count() == 1:
            return iter(search_results).next()
        raise LookupError(token)

    def searchForTerms(self, query=None, vocab_filter=None):
        """See `IHugeVocabulary`."""
        user = getUtility(ILaunchBag).user
        collection = self._getCollection().visibleByUser(user)
        if query is None:
            repositories = collection.getRepositories(eager_load=False)
        else:
            repositories = collection.search(query)
        return CountableIterator(
            repositories.count(), repositories, self.toTerm)

    def __len__(self):
        """See `IVocabulary`."""
        return self.search().count()

    def _getCollection(self):
        return getUtility(IAllGitRepositories)


class GitRepositoryRestrictedOnProductVocabulary(GitRepositoryVocabulary):
    """A vocabulary for searching git repositories restricted on product."""

    def __init__(self, context):
        super(GitRepositoryRestrictedOnProductVocabulary, self).__init__(
            context)
        if IProduct.providedBy(self.context):
            self.product = self.context
        else:
            # An unexpected type.
            raise AssertionError('Unexpected context type')

    def _getCollection(self):
        return getUtility(IAllGitRepositories).inProject(
            self.product).isExclusive()
