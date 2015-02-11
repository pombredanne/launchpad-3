# Copyright 2015 Canonical Ltd.  This software is licensed under the
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
from lp.registry.interfaces.product import IProduct


class IGitNamespace(Interface):
    """A namespace that a Git repository lives in."""

    name = Attribute(
        "The name of the namespace. This is prepended to the repository name.")

    target = Attribute("The `IHasGitRepositories` for this namespace.")

    def createRepository(registrant, name, information_type=None,
                         date_created=None, with_hosting=True):
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


class IGitNamespaceSet(Interface):
    """Interface for getting Git repository namespaces."""

    def get(person, project=None, distribution=None, sourcepackagename=None):
        """Return the appropriate `IGitNamespace` for the given objects."""

    def interpret(person, project, distribution, sourcepackagename):
        """Like `get`, but takes names of objects.

        :raise NoSuchPerson: If the person referred to cannot be found.
        :raise NoSuchProduct: If the project referred to cannot be found.
        :raise NoSuchDistribution: If the distribution referred to cannot be
            found.
        :raise NoSuchSourcePackageName: If the sourcepackagename referred to
            cannot be found.
        :return: An `IGitNamespace`.
        """

    def parse(namespace_name):
        """Parse 'namespace_name' into its components.

        The name of a namespace is actually a path containing many elements,
        each of which maps to a particular kind of object in Launchpad.
        Elements that can appear in a namespace name are: 'person',
        'project', 'distribution', and 'sourcepackagename'.

        `parse` returns a dict which maps the names of these elements (e.g.
        'person', 'project') to the values of these elements (e.g. 'mark',
        'firefox').  If the given path doesn't include a particular kind of
        element, the dict maps that element name to None.

        For example::
            parse('~foo/bar') => {
                'person': 'foo', 'project': 'bar', 'distribution': None,
                'sourcepackagename': None,
                }

        If the given 'namespace_name' cannot be parsed, then we raise an
        `InvalidNamespace` error.

        :raise InvalidNamespace: If the name is too long, too short, or
            malformed.
        :return: A dict with keys matching each component in
            'namespace_name'.
        """

    def lookup(namespace_name):
        """Return the `IGitNamespace` for 'namespace_name'.

        :raise InvalidNamespace: if namespace_name cannot be parsed.
        :raise NoSuchPerson: if the person referred to cannot be found.
        :raise NoSuchProduct: if the project referred to cannot be found.
        :raise NoSuchDistribution: if the distribution referred to cannot be
            found.
        :raise NoSuchSourcePackageName: if the sourcepackagename referred to
            cannot be found.
        :return: An `IGitNamespace`.
        """

    def traverse(segments):
        """Look up the Git repository at the path given by 'segments'.

        The iterable 'segments' will be consumed until a repository is
        found.  As soon as a repository is found, the repository will be
        returned and the consumption of segments will stop.  Thus, there
        will often be unconsumed segments that can be used for further
        traversal.

        :param segments: An iterable of names of Launchpad components.
            The first segment is the username, *not* preceded by a '~`.
        :raise InvalidNamespace: if there are not enough segments to define a
            repository.
        :raise NoSuchPerson: if the person referred to cannot be found.
        :raise NoSuchProduct: if the product or distro referred to cannot be
            found.
        :raise NoSuchDistribution: if the distribution referred to cannot be
            found.
        :raise NoSuchSourcePackageName: if the sourcepackagename referred to
            cannot be found.
        :return: `IGitRepository`.
        """


def get_git_namespace(target, owner):
    if IProduct.providedBy(target):
        return getUtility(IGitNamespaceSet).get(owner, project=target)
    elif IDistributionSourcePackage.providedBy(target):
        return getUtility(IGitNamespaceSet).get(
            owner, distribution=target.distribution,
            sourcepackagename=target.sourcepackagename)
    else:
        return getUtility(IGitNamespaceSet).get(owner)


def split_git_unique_name(unique_name):
    """Return the namespace and repository names of a unique name."""
    try:
        namespace_name, literal, repository_name = unique_name.rsplit("/", 2)
    except ValueError:
        raise InvalidNamespace(unique_name)
    if literal != "g":
        raise InvalidNamespace(unique_name)
    return namespace_name, repository_name
