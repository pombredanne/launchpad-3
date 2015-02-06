# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces relating to targets of Git repositories."""

__metaclass__ = type

__all__ = [
    'IHasGitRepositories',
    'IHasGitRepositoriesEdit',
    'IHasGitRepositoriesView',
    ]

from zope.interface import Interface


class IHasGitRepositoriesView(Interface):
    """Viewing an object that has related Git repositories."""

    def getGitRepositories(visible_by_user=None, eager_load=False):
        """Returns all Git repositories related to this object.

        :param visible_by_user: Normally the user who is asking.
        :param eager_load: If True, load related objects for the whole
            collection.
        :returns: A list of `IGitRepository` objects.
        """


class IHasGitRepositoriesEdit(Interface):
    """Editing an object that has related Git repositories."""

    def createGitRepository(registrant, owner, name, information_type=None):
        """Create a Git repository for this target and return it.

        :param registrant: The `IPerson` who registered the new repository.
        :param owner: The `IPerson` who owns the new repository.
        :param name: The repository name.
        :param information_type: Set the repository's information type to
            one different from the target's default.  The type must conform
            to the target's code sharing policy.  (optional)
        """


class IHasGitRepositories(IHasGitRepositoriesView, IHasGitRepositoriesEdit):
    """An object that has related Git repositories.

    A project contains Git repositories, a source package on a distribution
    contains branches, and a person contains "personal" branches.
    """
