# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface for objects that have a default Git repository.

A default Git repository is a repository that's somehow officially related
to an object.  It might be a project, a distribution source package, or a
combination of one of those with an owner to represent that owner's default
repository for that target.
"""

__metaclass__ = type
__all__ = [
    'get_default_git_repository',
    'ICanHasDefaultGitRepository',
    ]

from zope.interface import (
    Attribute,
    Interface,
    )

from lp.code.errors import (
    CannotHaveDefaultGitRepository,
    NoDefaultGitRepository,
    )


class ICanHasDefaultGitRepository(Interface):
    """Something that has a default Git repository."""

    context = Attribute("The object that can have a default Git repository.")
    repository = Attribute("The default Git repository.")
    path = Attribute(
        "The path for the default Git repository. "
        "Note that this will be set even if there is no default repository.")

    def setRepository(repository):
        """Set the default repository.

        :param repository: An `IGitRepository`.  After calling this,
            `ICanHasDefaultGitRepository.repository` will be `repository`.
        """


def get_default_git_repository(provided):
    """Get the `ICanHasDefaultGitRepository` for 'provided', whatever that is.

    :raise CannotHaveDefaultGitRepository: If 'provided' can never have a
        default Git repository.
    :raise NoDefaultGitRepository: If 'provided' could have a default Git
        repository, but doesn't.
    :return: The `ICanHasDefaultGitRepository` object.
    """
    has_default_repository = ICanHasDefaultGitRepository(provided, None)
    if has_default_repository is None:
        raise CannotHaveDefaultGitRepository(provided)
    if has_default_repository.repository is None:
        raise NoDefaultGitRepository(provided)
    return has_default_repository
