# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211, E0213

"""A collection of branches.

See `IBranchCollection` for more details.
"""

__metaclass__ = type
__all__ = [
    'IAllBranches',
    'IBranchCollection',
    'InvalidFilter',
    ]

from zope.interface import Interface


class InvalidFilter(Exception):
    """Raised when an `IBranchCollection` cannot apply the given filter."""


class IBranchCollection(Interface):
    """A collection of branches.

    An `IBranchCollection` is an immutable collection of branches. It has two
    kinds of methods: filter methods and query methods.

    Query methods get information about the contents of collection. See
    `IBranchCollection.count` and `IBranchCollection.getBranches`.

    Filter methods return new IBranchCollection instances that have some sort
    of restriction. Examples include `ownedBy`, `visibleByUser` and
    `inProduct`.

    Implementations of this interface are not 'content classes'. That is, they
    do not correspond to a particular row in the database.

    This interface is intended for use within Launchpad, not to be exported as
    a public API.
    """

    # Note to developers: This interface should be extended with more query
    # methods. It would be great to have methods like getRecentRevisions on
    # arbitrary branch collections. Other statistical methods would be good
    # too, e.g. number of different branch owners in this collection.

    def count():
        """The number of branches in this collection."""

    def getBranches(join_owner=True, join_product=True):
        """Return a result set of all branches in this collection.

        The returned result set will also join across the specified tables as
        defined by the arguments to this function.  These extra tables are
        joined specificly to allow the caller to sort on values not in the
        Branch table itself.

        XXX TimPenhey 2009-03-16, spec=package-branches
        When we have extra sorting columns in the views on source package
        branches, we'll have to update the parameters to this method.  Ideally
        we'll come up with a cleaner interface.  If we don't then a source
        package listing, which obviously won't have a "Sort by Project name"
        will be joining across the Product table (which will be empty anyway)
        and slowing down the query.  By having these parameters, we can make
        the queries for the counting and branch id queries much faster.

        :param join_owner: Join the Person table with the Branch.owner.
        :param join_product: Left Join the Product table with Branch.product.
        """

    def getMergeProposals(statuses=None, for_branches=None):
        """Return a result set of merge proposals for the branches in this
        collection.

        :param statuses: If specified, only return merge proposals with these
            statuses. If not, return all merge proposals.
        :param for_branches: An iterable of branches what will restrict the
            resulting set of merge proposals to be only those for the
            branches specified.
        """

    def getMergeProposalsForReviewer(reviewer, status=None):
        """Return a result set of merge proposals for the given reviewer.

        That is, all merge proposals that 'reviewer' has voted on or has been
        invited to vote on.

        :param reviewer: An `IPerson` who is a reviewer.
        :param status: An iterable of queue_status of the proposals to return.
            If None is specified, all the proposals of all possible states
            are returned.
        """

    def inProduct(product):
        """Restrict the collection to branches in 'product'."""

    def inProject(project):
        """Restrict the collection to branches in 'project'."""

    def inSourcePackage(package):
        """Restrict the collection to branches in 'package'."""

    def ownedBy(person):
        """Restrict the collection to branches owned by 'person'."""

    def registeredBy(person):
        """Restrict the collection to branches registered by 'person'."""

    def relatedTo(person):
        """Restrict the collection to branches related to 'person'.

        That is, branches that 'person' owns, registered or is subscribed to.
        """

    def search(search_term):
        """Search the collection for branches matching 'search_term'.

        :param search_term: A string.
        :return: An `ICountableIterator`.
        """

    def scanned():
        """Restrict the collection to branches that have been scanned."""

    def subscribedBy(person):
        """Restrict the collection to branches subscribed to by 'person'."""

    def visibleByUser(person):
        """Restrict the collection to branches that person is allowed to see.
        """

    def withBranchType(*branch_types):
        """Restrict the collection to branches with the given branch types."""

    def withLifecycleStatus(*statuses):
        """Restrict the collection to branches with the given statuses."""


class IAllBranches(IBranchCollection):
    """An `IBranchCollection` representing all branches in Launchpad."""
