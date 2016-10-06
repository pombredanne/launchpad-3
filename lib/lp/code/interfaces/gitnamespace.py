# Copyright 2015-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface for a Git repository namespace."""

__metaclass__ = type
__all__ = [
    'get_git_namespace',
    'IGitNamespace',
    'IGitNamespacePolicy',
    'IGitNamespaceSet',
    'split_git_unique_name',
    ]

from zope.component import getUtility
from zope.interface import (
    Attribute,
    Interface,
    )

from lp.code.errors import InvalidNamespace
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.product import IProduct


class IGitNamespace(Interface):
    """A namespace that a Git repository lives in."""

    name = Attribute(
        "The name of the namespace. This is prepended to the repository name.")

    target = Attribute("The `IHasGitRepositories` for this namespace.")

    def createRepository(repository_type, registrant, name,
                         information_type=None, date_created=None):
        """Create and return an `IGitRepository` in this namespace."""

    def isNameUsed(name):
        """Is 'name' already used in this namespace?"""

    def findUnusedName(prefix):
        """Find an unused repository name starting with 'prefix'.

        Note that there is no guarantee that the name returned by this method
        will remain unused for very long.
        """

    def moveRepository(repository, mover, new_name=None,
                       rename_if_necessary=False):
        """Move the repository into this namespace.

        :param repository: The `IGitRepository` to move.
        :param mover: The `IPerson` doing the moving.
        :param new_name: A new name for the repository.
        :param rename_if_necessary: Rename the repository if the repository
            name already exists in this namespace.
        :raises GitRepositoryCreatorNotMemberOfOwnerTeam: if the namespace
            owner is a team and 'mover' is not in that team.
        :raises GitRepositoryCreatorNotOwner: if the namespace owner is an
            individual and 'mover' is not the owner.
        :raises GitRepositoryCreationForbidden: if 'mover' is not allowed to
            create a repository in this namespace due to privacy rules.
        :raises GitRepositoryExists: if a repository with the new name
            already exists in the namespace, and 'rename_if_necessary' is
            False.
        """

    def getRepositories():
        """Return the repositories in this namespace."""

    def getByName(repository_name, default=None):
        """Find the repository in this namespace called 'repository_name'.

        :return: `IGitRepository` if found, otherwise 'default'.
        """

    def __eq__(other):
        """Is this namespace the same as another namespace?"""

    def __ne__(other):
        """Is this namespace not the same as another namespace?"""


class IGitNamespacePolicy(Interface):
    """Methods relating to Git repository creation and validation."""

    has_defaults = Attribute(
        "True iff the target of this namespace may have a default repository.")

    allow_push_to_set_default = Attribute(
        "True iff this namespace permits automatically setting a default "
        "repository on push.")

    supports_merge_proposals = Attribute(
        "Does this namespace support merge proposals at all?")

    supports_code_imports = Attribute(
        "Does this namespace support code imports at all?")

    allow_recipe_name_from_target = Attribute(
        "Can recipe names reasonably be generated from the target name "
        "rather than the branch name?")

    def getAllowedInformationTypes(who):
        """Get the information types that a repository in this namespace can
        have.

        :param who: The user making the request.
        :return: A sequence of `InformationType`s.
        """

    def getDefaultInformationType(who):
        """Get the default information type for repositories in this namespace.

        :param who: The user to return the information type for.
        :return: An `InformationType`.
        """

    def validateRegistrant(registrant):
        """Check that the registrant can create a repository in this namespace.

        :param registrant: An `IPerson`.
        :raises GitRepositoryCreatorNotMemberOfOwnerTeam: if the namespace
            owner is a team and the registrant is not in that team.
        :raises GitRepositoryCreatorNotOwner: if the namespace owner is an
            individual and the registrant is not the owner.
        :raises GitRepositoryCreationForbidden: if the registrant is not
            allowed to create a repository in this namespace due to privacy
            rules.
        """

    def validateRepositoryName(name):
        """Check the repository `name`.

        :param name: A branch name, either string or unicode.
        :raises GitRepositoryExists: if a branch with the `name` already
            exists in the namespace.
        :raises LaunchpadValidationError: if the name doesn't match the
            validation constraints on IGitRepository.name.
        """

    def validateDefaultFlags(repository):
        """Check that any default flags on 'repository' fit this namespace.

        :param repository: An `IGitRepository` to check.
        :raises GitDefaultConflict: If the repository has the target_default
            flag set but this namespace already has a target default, or if
            the repository has the owner_default flag set but this namespace
            already has an owner-target default.
        """

    def validateMove(repository, mover, name=None):
        """Check that 'mover' can move 'repository' into this namespace.

        :param repository: An `IGitRepository` that might be moved.
        :param mover: The `IPerson` who would move it.
        :param name: A new name for the repository.  If None, the repository
            name is used.
        :raises GitRepositoryCreatorNotMemberOfOwnerTeam: if the namespace
            owner is a team and 'mover' is not in that team.
        :raises GitRepositoryCreatorNotOwner: if the namespace owner is an
            individual and 'mover' is not the owner.
        :raises GitRepositoryCreationForbidden: if 'mover' is not allowed to
            create a repository in this namespace due to privacy rules.
        :raises GitRepositoryExists: if a repository with the new name
            already exists in the namespace.
        """

    def areRepositoriesMergeable(other_namespace):
        """Are repositories from other_namespace mergeable into this one?"""

    collection = Attribute("An `IGitCollection` for this namespace.")

    def assignKarma(person, action_name, date_created=None):
        """Assign karma to the person on the appropriate target."""


class IGitNamespaceSet(Interface):
    """Interface for getting Git repository namespaces."""

    def get(person, project=None, distribution=None, sourcepackagename=None):
        """Return the appropriate `IGitNamespace` for the given objects."""


def get_git_namespace(target, owner):
    if IProduct.providedBy(target):
        return getUtility(IGitNamespaceSet).get(owner, project=target)
    elif IDistributionSourcePackage.providedBy(target):
        return getUtility(IGitNamespaceSet).get(
            owner, distribution=target.distribution,
            sourcepackagename=target.sourcepackagename)
    elif target is None or IPerson.providedBy(target):
        return getUtility(IGitNamespaceSet).get(owner)
    else:
        raise AssertionError("No Git namespace defined for %s" % target)


# Marker for references to Git URL layouts: ##GITNAMESPACE##
def split_git_unique_name(unique_name):
    """Return the namespace and repository names of a unique name."""
    try:
        namespace_name, literal, repository_name = unique_name.rsplit("/", 2)
    except ValueError:
        raise InvalidNamespace(unique_name)
    if literal != "+git":
        raise InvalidNamespace(unique_name)
    return namespace_name, repository_name
