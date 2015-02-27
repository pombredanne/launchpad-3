# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'HasGitRepositoriesMixin',
    ]

from zope.component import getUtility

from lp.code.interfaces.gitcollection import IGitCollection
from lp.code.interfaces.gitrepository import IGitRepositorySet


class HasGitRepositoriesMixin:
    """A mixin implementation for `IHasGitRepositories`."""

    def createGitRepository(self, registrant, owner, name,
                            information_type=None):
        """See `IHasGitRepositories`."""
        return getUtility(IGitRepositorySet).new(
            registrant, owner, self, name,
            information_type=information_type)

    def getGitRepositories(self, visible_by_user=None, eager_load=False):
        """See `IHasGitRepositories`."""
        collection = IGitCollection(self).visibleByUser(visible_by_user)
        return collection.getRepositories(eager_load=eager_load)
