# Copyright 2015-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A collection of Git repositories.

See `IGitCollection` for more details.
"""

__metaclass__ = type
__all__ = [
    'IAllGitRepositories',
    'IGitCollection',
    'InvalidGitFilter',
    ]

from zope.interface import Interface


class InvalidGitFilter(Exception):
    """Raised when an `IGitCollection` cannot apply the given filter."""


class IGitCollection(Interface):
    """A collection of Git repositories.

    An `IGitCollection` is an immutable collection of Git repositories. It
    has two kinds of methods: filter methods and query methods.

    Query methods get information about the contents of the collection. See
    `IGitCollection.count` and `IGitCollection.getRepositories`.

    Filter methods return new IGitCollection instances that have some sort
    of restriction. Examples include `ownedBy`, `visibleByUser` and
    `inProject`.

    Implementations of this interface are not 'content classes'. That is, they
    do not correspond to a particular row in the database.

    This interface is intended for use within Launchpad, not to be exported as
    a public API.
    """

    def count():
        """The number of repositories in this collection."""

    def is_empty():
        """Is this collection empty?"""

    def ownerCounts():
        """Return the number of different repository owners.

        :return: a tuple (individual_count, team_count) containing the
            number of individuals and teams that own repositories in this
            collection.
        """

    def getRepositories(eager_load=False, order_by_date=False,
                        order_by_id=False):
        """Return a result set of all repositories in this collection.

        The returned result set will also join across the specified tables
        as defined by the arguments to this function.  These extra tables
        are joined specifically to allow the caller to sort on values not in
        the GitRepository table itself.

        :param eager_load: If True trigger eager loading of all the related
            objects in the collection.
        :param order_by_date: If True, order results by descending
            modification date.
        :param order_by_id: If True, order results by ascending ID.
        """

    def getRepositoryIds():
        """Return a result set of all repository ids in this collection."""

    # XXX cjwatson 2015-04-16: Add something like for_repositories or
    # for_refs once we know exactly what we need.
    def getMergeProposals(statuses=None, target_repository=None,
                          target_path=None, prerequisite_repository=None,
                          prerequisite_path=None, eager_load=False):
        """Return a result set of merge proposals for the repositories in
        this collection.

        :param statuses: If specified, only return merge proposals with these
            statuses. If not, return all merge proposals.
        :param target_repository: If specified, only return merge proposals
            that target the specified repository.
        :param target_path: If specified, only return merge proposals that
            target the specified path.
        :param prerequisite_repository: If specified, only return merge
            proposals that require a reference in the specified repository to
            be merged first.
        :param prerequisite_path: If specified, only return merge proposals
            that require a reference with the specified path to be merged
            first.
        :param eager_load: If True, preloads all the related information for
            merge proposals like PreviewDiffs and GitRepositories.
        """

    def getMergeProposalsForPerson(person, status=None):
        """Proposals for `person`.

        Return the proposals for repositories owned by `person` or where
        `person` is reviewing or been asked to review.
        """

    def getMergeProposalsForReviewer(reviewer, status=None):
        """Return a result set of merge proposals for the given reviewer.

        That is, all merge proposals that 'reviewer' has voted on or has
        been invited to vote on.

        :param reviewer: An `IPerson` who is a reviewer.
        :param status: An iterable of queue_status of the proposals to
            return.  If None is specified, all the proposals of all possible
            states are returned.
        """

    def getGrantsForGrantee(grantee):
        """Return a result set of access grants to the given grantee.

        :param grantee: An `IPerson`.
        """

    def getTeamsWithRepositories(person):
        """Return the teams that person is a member of that have
        repositories."""

    def inProject(project):
        """Restrict the collection to repositories in 'project'."""

    def inProjectGroup(projectgroup):
        """Restrict the collection to repositories in 'projectgroup'."""

    def inDistribution(distribution):
        """Restrict the collection to repositories in 'distribution'."""

    def inDistributionSourcePackage(distro_source_package):
        """Restrict to repositories in a package for a distribution."""

    def isPersonal():
        """Restrict the collection to personal repositories."""

    def isPrivate():
        """Restrict the collection to private repositories."""

    def isExclusive():
        """Restrict the collection to repositories owned by exclusive
        people."""

    def ownedBy(person):
        """Restrict the collection to repositories owned by 'person'."""

    def ownedByTeamMember(person):
        """Restrict the collection to repositories owned by 'person' or a
        team of which person is a member.
        """

    def registeredBy(person):
        """Restrict the collection to repositories registered by 'person'."""

    def search(term):
        """Search the collection for repositories matching 'term'.

        :param term: A string.
        :return: A `ResultSet` of repositories that matched.
        """

    def subscribedBy(person):
        """Restrict the collection to repositories subscribed to by
        'person'."""

    def targetedBy(person, since=None):
        """Restrict the collection to repositories targeted by person.

        A repository is targeted by a person if that person has registered a
        merge proposal with a reference in that repository as the target.

        :param since: If supplied, ignore merge proposals before this date.
        """

    def visibleByUser(person):
        """Restrict the collection to repositories that person is allowed to
        see."""

    def withIds(*repository_ids):
        """Restrict the collection to repositories with the specified ids."""


class IAllGitRepositories(IGitCollection):
    """A `IGitCollection` representing all Git repositories in Launchpad."""
