# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Implementations of `IBranchCollection`."""

__metaclass__ = type
__all__ = [
    'GenericBranchCollection',
    ]

from storm.expr import And, LeftJoin, Join, Or, Select, Union

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet)
from canonical.launchpad.database.branch import Branch
from canonical.launchpad.database.branchsubscription import BranchSubscription
from canonical.launchpad.database.distribution import Distribution
from canonical.launchpad.database.distroseries import DistroSeries
from canonical.launchpad.database.person import Owner
from canonical.launchpad.database.product import Product
from canonical.launchpad.database.sourcepackagename import SourcePackageName
from canonical.launchpad.database.teammembership import TeamParticipation
from canonical.launchpad.interfaces.branch import (
    IBranchSet, user_has_special_branch_access)
from canonical.launchpad.interfaces.branchcollection import IBranchCollection
from canonical.launchpad.interfaces.codehosting import LAUNCHPAD_SERVICES
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.launchpad.webapp.vocabulary import CountableIterator


class GenericBranchCollection:
    """See `IBranchCollection`."""

    implements(IBranchCollection)

    def __init__(self, store=None, branch_filter_expressions=None,
                 tables=None, exclude_from_search=None):
        """Construct a `GenericBranchCollection`.

        :param store: The store to look in for branches. If not specified,
            use the default store.
        :param branch_filter_expressions: A list of Storm expressions to
            restrict the branches in the collection. If unspecified, then
            there will be no restrictions on the result set. That is, all
            branches in the store will be in the collection.
        :param tables: The Storm tables to query on. If an expression in
            branch_filter_expressions refers to a table, then that table
            *must* be in this list. `GenericBranchCollection` will use the
            `Branch` table, the `Person` table aliased as `Owner` and the
            `Product` table if unspecified.
        """
        self._store = store
        if branch_filter_expressions is None:
            branch_filter_expressions = []
        self._branch_filter_expressions = branch_filter_expressions
        if tables is None:
            # Join in Product and the Person table as 'Owner' so that we can
            # sort the results by product name and owner name.
            tables = [Branch, LeftJoin(Product, Branch.product == Product.id),
                      Join(Owner, Branch.owner == Owner.id)]
        self._tables = tables
        if exclude_from_search is None:
            exclude_from_search = []
        self._exclude_from_search = exclude_from_search

    def count(self):
        """See `IBranchCollection`."""
        return self.getBranches().count()

    def _filterBy(self, expressions, tables=None, exclude_from_search=None):
        """Return a subset of this collection, filtered by 'expressions'."""
        # NOTE: JonathanLange 2009-02-17: We might be able to avoid the need
        # for explicit 'tables' by harnessing Storm's table inference system.
        # See http://paste.ubuntu.com/118711/ for one way to do that.
        if tables is None:
            tables = []
        if exclude_from_search is None:
            exclude_from_search = []
        if expressions is None:
            expressions = []
        return self.__class__(
            self._store,
            self._branch_filter_expressions + expressions,
            self._tables + tables,
            self._exclude_from_search + exclude_from_search)

    def getBranches(self):
        """See `IBranchCollection`."""
        # Although you might think we could set the default value for store in
        # the constructor, we can't. The IStoreSelector utility is not
        # available at the time that the branchcollection.zcml is parsed,
        # which means we get an error if this code is in the constructor.
        # -- JonathanLange 2009-02-17.
        if self._store is None:
            store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        else:
            store = self._store
        results = store.using(*(self._tables)).find(
            Branch, *(self._branch_filter_expressions))
        def identity(x):
            return x
        # Decorate the result set to work around bug 217644.
        return DecoratedResultSet(results, identity)

    def inProduct(self, product):
        """See `IBranchCollection`."""
        return self._filterBy(
            [Branch.product == product], exclude_from_search=['product'])

    def inProject(self, project):
        """See `IBranchCollection`."""
        return self._filterBy([Product.project == project.id])

    def inSourcePackage(self, source_package):
        """See `IBranchCollection`."""
        return self._filterBy([
            Branch.distroseries == source_package.distroseries,
            Branch.sourcepackagename == source_package.sourcepackagename])

    def ownedBy(self, person):
        """See `IBranchCollection`."""
        return self._filterBy([Branch.owner == person])

    def registeredBy(self, person):
        """See `IBranchCollection`."""
        return self._filterBy([Branch.registrant == person])

    def relatedTo(self, person):
        """See `IBranchCollection`."""
        return self._filterBy(
            [Branch.id.is_in(
                Union(
                    Select(Branch.id, Branch.owner == person),
                    Select(Branch.id, Branch.registrant == person),
                    Select(Branch.id,
                           And(BranchSubscription.person == person,
                               BranchSubscription.branch == Branch.id))))])

    def _getExactMatch(self, search_term):
        """Return the exact branch that 'search_term' matches, or None."""
        search_term = search_term.rstrip('/')
        branch_set = getUtility(IBranchSet)
        branch = branch_set.getByUniqueName(search_term)
        if branch is None:
            branch = branch_set.getByUrl(search_term)
        return branch

    def search(self, search_term):
        """See `IBranchCollection`."""
        # XXX: JonathanLange 2009-02-23: This matches the old search algorithm
        # that used to live in vocabularies/dbojects.py. It's not actually
        # very good -- really it should match based on substrings of the
        # unique name and sort based on relevance.
        branch = self._getExactMatch(search_term)
        if branch is not None:
            if branch in self.getBranches():
                return CountableIterator(1, [branch])
            else:
                return CountableIterator(0, [])
        like_term = '%' + search_term + '%'
        # Match the Branch name or the URL.
        queries = [Select(Branch.id,
                          Or(Branch.name.like(like_term),
                             Branch.url == search_term))]
        # Match the product name.
        if 'product' not in self._exclude_from_search:
            queries.append(Select(
                Branch.id,
                And(Branch.product == Product.id,
                    Product.name.like(like_term))))

        # Match the owner name.
        queries.append(Select(
            Branch.id,
            And(Branch.owner == Owner.id, Owner.name.like(like_term))))

        # Match the package bits.
        queries.append(
            Select(Branch.id,
                   And(Branch.sourcepackagename == SourcePackageName.id,
                       Branch.distroseries == DistroSeries.id,
                       DistroSeries.distribution == Distribution.id,
                       Or(SourcePackageName.name.like(like_term),
                          DistroSeries.name.like(like_term),
                          Distribution.name.like(like_term)))))

        # Get the results.
        collection = self._filterBy([Branch.id.is_in(Union(*queries))])
        results = collection.getBranches().order_by(Branch.name, Branch.id)
        return CountableIterator(results.count(), results)

    def scanned(self):
        """See `IBranchCollection`."""
        return self._filterBy([Branch.last_scanned != None])

    def subscribedBy(self, person):
        """See `IBranchCollection`."""
        return self._filterBy(
            [BranchSubscription.person == person],
            [Join(BranchSubscription,
                  BranchSubscription.branch == Branch.id)])

    def visibleByUser(self, person):
        """See `IBranchCollection`."""
        if (person == LAUNCHPAD_SERVICES or
            user_has_special_branch_access(person)):
            return self
        # Everyone can see public branches.
        public_branches = Select(Branch.id, Branch.private == False)

        if person is None:
            # Anonymous users can only see the public branches.
            visible_branches = public_branches
        else:
            # A union is used here rather than the more simplistic simple
            # joins due to the query plans generated.  If we just have a
            # simple query then we are joining across TeamParticipation and
            # BranchSubscription.  This creates a bad plan, hence the use of a
            # union.
            visible_branches = Union(
                public_branches,
                # Branches the person owns (or a team the person is in).
                Select(Branch.id,
                       And(Branch.owner == TeamParticipation.teamID,
                           TeamParticipation.person == person)),
                # Private branches the person is subscribed to, either
                # directly or indirectly.
                Select(Branch.id,
                       And(BranchSubscription.branch == Branch.id,
                           BranchSubscription.person ==
                               TeamParticipation.teamID,
                           TeamParticipation.person == person,
                           Branch.private == True)))
        return self._filterBy([Branch.id.is_in(visible_branches)])

    def withBranchType(self, *branch_types):
        return self._filterBy([Branch.branch_type.is_in(branch_types)])

    def withLifecycleStatus(self, *statuses):
        """See `IBranchCollection`."""
        return self._filterBy([Branch.lifecycle_status.is_in(statuses)])
