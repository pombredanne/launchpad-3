# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Vocabularies that contain Git repositories."""

__metaclass__ = type

__all__ = [
    'GitRepositoryVocabulary',
    ]

from zope.component import getUtility
from zope.interface import implements
from zope.schema.vocabulary import SimpleTerm

from lp.code.interfaces.gitcollection import IAllGitRepositories
from lp.code.model.gitrepository import GitRepository
from lp.services.webapp.interfaces import ILaunchBag
from lp.services.webapp.vocabulary import (
    CountableIterator,
    IHugeVocabulary,
    SQLObjectVocabularyBase,
    )


class GitRepositoryVocabulary(SQLObjectVocabularyBase):
    """A vocabulary for searching Git repositories."""

    implements(IHugeVocabulary)

    _table = GitRepository
    _orderBy = ['name', 'id']
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